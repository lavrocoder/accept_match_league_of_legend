import threading
import time
from typing import Optional

import eel

from app.clients.lcu_api import Client
from app.config import CONFIG_FILE, BASE_CONFIG_FILE, CHAMPIONS_FILE
from app.database import PresetsDatabase
from app.models.schemas import Champions, Champion
from app.services.updater import ProjectUpdater
from app.utils import (
    get_or_download_champions,
    get_champions_for_role_by_mastery,
    load_champions,
    get_current_queue,
    get_role_name,
    find_available_champion
)
from app.utils.get_champions_for_role import get_champions_for_role

# Global API instance for lobby updates
_api_instance: Optional['Client'] = None
_queues_cache: list = []
_ddragon_data_cache = None
_presets_db: Optional[PresetsDatabase] = None


def get_presets_db() -> PresetsDatabase:
    """Get or create presets database instance"""
    global _presets_db
    if _presets_db is None:
        _presets_db = PresetsDatabase()
    return _presets_db


class AutoMatchBot:
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Settings
        self.auto_accept = True
        self.auto_ban = True
        self.auto_pick = True

        # State
        self.match_accepted = False
        self.is_connected = False
        self.last_phase = None
        self.current_role = None
        self.role_printed = False
        self.champions_for_role: Optional[Champions] = None
        self.ban_completed = False
        self.pick_completed = False
        self.queues = []

        # Data
        self.ddragon_data = None
        self.champions = None

    def log(self, message: str, log_type: str = "info"):
        """Send log message to UI"""
        try:
            eel.addLog(message, log_type)
        except Exception:
            print(f"[{log_type.upper()}] {message}")

    def update_connection(self, connected: bool, text: str):
        """Update connection status in UI"""
        try:
            eel.updateConnectionStatus(connected, text)
        except Exception:
            pass
        self.is_connected = connected

    def update_phase(self, phase: str):
        """Update current phase in UI"""
        try:
            eel.updatePhase(phase)
        except Exception:
            pass

    def update_role(self, role: str):
        """Update current role in UI"""
        try:
            eel.updateRole(role)
        except Exception:
            pass

    def update_champions_table(self):
        """Send champions data to UI"""
        if self.champions_for_role is None:
            return

        try:
            data = {
                'top': [{'name': c.name, 'id': c.id} for c in self.champions_for_role.top[:10]],
                'top_ban': [{'name': c.name, 'id': c.id} for c in self.champions_for_role.top_ban[:10]],
                'jungle': [{'name': c.name, 'id': c.id} for c in self.champions_for_role.jungle[:10]],
                'jungle_ban': [{'name': c.name, 'id': c.id} for c in self.champions_for_role.jungle_ban[:10]],
                'middle': [{'name': c.name, 'id': c.id} for c in self.champions_for_role.middle[:10]],
                'middle_ban': [{'name': c.name, 'id': c.id} for c in self.champions_for_role.middle_ban[:10]],
                'bottom': [{'name': c.name, 'id': c.id} for c in self.champions_for_role.bottom[:10]],
                'bottom_ban': [{'name': c.name, 'id': c.id} for c in self.champions_for_role.bottom_ban[:10]],
                'utility': [{'name': c.name, 'id': c.id} for c in self.champions_for_role.utility[:10]],
                'utility_ban': [{'name': c.name, 'id': c.id} for c in self.champions_for_role.utility_ban[:10]],
            }
            eel.updateChampionsTable(data)
        except Exception:
            pass

    def update_lobby(self, api):
        """Send lobby members to UI"""
        try:
            members = api.get_lobby_members()
            if not members:
                eel.updateLobby([])
                return

            lobby_data = []
            for member in members:
                puuid = member.get("puuid")
                game_name = member.get("gameName", "")
                tag_line = member.get("gameTag", "")

                if not game_name:
                    summoner_info = api.get_summoner_by_puuid(puuid)
                    if summoner_info:
                        game_name = summoner_info.get("gameName", summoner_info.get("displayName", "Unknown"))
                        tag_line = summoner_info.get("tagLine", "")

                riot_id = f"{game_name}#{tag_line}" if tag_line else game_name

                # Get ranks
                solo_rank_str = "Unranked"
                flex_rank_str = "Unranked"
                ranked_stats = api.get_ranked_stats(puuid)
                if ranked_stats:
                    queues = ranked_stats.get("queues", [])
                    for queue in queues:
                        queue_type = queue.get("queueType", "")
                        if queue_type == "RANKED_SOLO_5x5":
                            solo_rank_str = self._format_rank(queue)
                        elif queue_type == "RANKED_FLEX_SR":
                            flex_rank_str = self._format_rank(queue)

                lobby_data.append({
                    'name': riot_id,
                    'isLeader': member.get("isLeader", False),
                    'ready': member.get("ready", False),
                    'soloRank': solo_rank_str,
                    'flexRank': flex_rank_str
                })

            eel.updateLobby(lobby_data)
        except Exception:
            pass

    def _format_rank(self, queue_data):
        """Format rank to readable form"""
        if not queue_data:
            return "Unranked"

        tier = queue_data.get("tier", "")
        division = queue_data.get("division", "")
        lp = queue_data.get("leaguePoints", 0)

        if not tier or tier == "NONE":
            return "Unranked"

        tier_formatted = tier.capitalize()

        if tier in ["CHALLENGER", "GRANDMASTER", "MASTER"]:
            return f"{tier_formatted} {lp} LP"

        return f"{tier_formatted} {division} ({lp} LP)"

    def reset_state(self):
        """Reset bot state"""
        self.match_accepted = False
        self.last_phase = None
        self.current_role = None
        self.role_printed = False
        self.ban_completed = False
        self.pick_completed = False
        self.queues = []

    def load_data(self):
        """Load champion data"""
        global _ddragon_data_cache
        self.log("Loading champions...", "info")
        self.ddragon_data = get_or_download_champions(CHAMPIONS_FILE)
        _ddragon_data_cache = self.ddragon_data

        # Load presets from database
        db = get_presets_db()
        if db.is_empty():
            # Import from file if database is empty
            self.champions = load_champions(CONFIG_FILE, BASE_CONFIG_FILE, self.ddragon_data)
            db.import_from_champions(self.champions)
            self.log("Presets imported to database", "info")
        else:
            # Load from database
            self.champions = self._load_champions_from_db()
        self.log("Presets loaded", "success")

    def _load_champions_from_db(self) -> Champions:
        """Load champions from database into Champions model"""
        db = get_presets_db()
        presets = db.get_all_presets()
        champs = Champions()

        for role in ['top', 'jungle', 'middle', 'bottom', 'utility']:
            # Load picks
            pick_list = presets.get(role, [])
            for p in pick_list:
                setattr(champs, role, getattr(champs, role) + [
                    Champion(id=p['id'], name=p['name'], alias='', level=0, points=0, by='Preset')
                ])

            # Load bans
            ban_list = presets.get(f'{role}_ban', [])
            for b in ban_list:
                setattr(champs, f'{role}_ban', getattr(champs, f'{role}_ban') + [
                    Champion(id=b['id'], name=b['name'], alias='', level=0, points=0, by='Preset')
                ])

        return champs

    def reload_presets(self):
        """Reload presets from database"""
        self.champions = self._load_champions_from_db()

    def run(self):
        """Main bot loop"""
        updater = ProjectUpdater()
        updater.check_for_updates()

        self.load_data()
        self.update_connection(False, "Waiting for client...")

        while self.running:
            try:
                port, token = Client.get_port_and_token()

                if port and token:
                    global _api_instance, _queues_cache
                    api = Client(port, token)
                    _api_instance = api

                    if not self.is_connected:
                        mastery = api.get_champions_mastery()
                        if mastery:
                            self.update_connection(True, "Connected to client")
                            self.log("Connected to client", "success")

                            recommended_positions = api.get_recommended_champion_positions()
                            champions_for_role_by_mastery = get_champions_for_role_by_mastery(
                                self.ddragon_data, mastery, recommended_positions
                            )
                            self.champions_for_role = get_champions_for_role(
                                champions_for_role_by_mastery, self.champions
                            )
                            self.update_champions_table()
                            self.queues = api.get_queues()
                            _queues_cache = self.queues

                    # Get current phase
                    current_phase = api.get_gameflow_phase()
                    session = api.get_session()

                    if session is None:
                        time.sleep(0.5)
                        continue

                    queue_id = session.get("gameData", {}).get("queue", {}).get("id")
                    queue_name = get_current_queue(self.queues, queue_id)

                    current_phase_name = f"{current_phase} - {queue_name}" if queue_name else current_phase

                    if current_phase_name != self.last_phase:
                        if current_phase:
                            self.log(f"Phase: {current_phase_name}", "phase")
                            self.update_phase(current_phase_name)

                            if current_phase == 'Matchmaking':
                                self.update_lobby(api)

                        self.last_phase = current_phase_name

                        if current_phase != "ChampSelect":
                            self.ban_completed = False
                            self.pick_completed = False
                            self.current_role = None
                            self.role_printed = False
                            self.update_role("-")

                    # Handle match found
                    if current_phase == "ReadyCheck" and self.auto_accept:
                        ready_check = api.check_match_found()

                        if ready_check and not self.match_accepted:
                            player_response = ready_check.get("playerResponse", "None")

                            if player_response == "None":
                                self.log(f"Match found! Mode: {queue_name}", "warning")
                                if api.accept_match():
                                    self.log("Match accepted!", "success")
                                    self.match_accepted = True
                                else:
                                    self.log("Failed to accept match", "error")
                            elif player_response == "Accepted":
                                self.match_accepted = True
                    else:
                        self.match_accepted = False

                    # Handle champion select
                    if current_phase == "ChampSelect":
                        if self.current_role is None:
                            self.current_role = api.get_my_assigned_role()

                        if self.champions_for_role:
                            pick_preset, ban_preset = self.champions_for_role.get_presets_for_role(
                                self.current_role
                            )

                            if not self.role_printed and self.current_role:
                                role_name = get_role_name(self.current_role)
                                self.log(f"Role: {role_name}", "info")
                                self.update_role(role_name)

                                ban_names = ', '.join([unit.name for unit in ban_preset[:10]])
                                pick_names = ', '.join([unit.name for unit in pick_preset[:10]])
                                self.log(f"Bans: {ban_names}", "info")
                                self.log(f"Picks: {pick_names}", "info")
                                self.role_printed = True

                            phase_info = api.get_phase_info()

                            # Handle ban phase
                            if not self.ban_completed and self.auto_ban:
                                if (phase_info and
                                    phase_info.get('phase') == 'BAN_PICK' and
                                    phase_info.get('current_action_type') == 'ban'):

                                    ban_action_id = phase_info.get('action_id')
                                    banned = api.get_banned_champions()
                                    champ = find_available_champion(ban_preset, banned)

                                    if champ:
                                        self.log(f"Banning: {champ.name}", "info")
                                        if api.perform_action(ban_action_id, champ.id, complete=True):
                                            self.log(f"{champ.name} banned!", "success")
                                            self.ban_completed = True
                                        else:
                                            self.log(f"Failed to ban {champ.name}", "error")
                                    else:
                                        self.log("No available champions for ban from preset", "warning")
                                        self.ban_completed = True

                            # Handle pick phase
                            if not self.pick_completed and self.auto_pick:
                                if (phase_info and
                                    phase_info.get('phase') == 'BAN_PICK' and
                                    phase_info.get('current_action_type') == 'pick' and
                                    phase_info.get('is_my_turn')):

                                    pick_action_id = phase_info.get('action_id')
                                    banned = api.get_banned_champions()
                                    picked = api.get_picked_champions()
                                    unavailable = banned | picked

                                    champ = find_available_champion(pick_preset, unavailable)

                                    if champ:
                                        self.log(f"Picking: {champ.name}", "info")
                                        if api.perform_action(pick_action_id, champ.id, complete=True):
                                            self.log(f"{champ.name} picked!", "success")
                                            self.pick_completed = True
                                        else:
                                            self.log(f"Failed to pick {champ.name}", "error")
                                    else:
                                        self.log("No available champions for pick from preset", "warning")
                                        self.pick_completed = True

                else:
                    if self.is_connected:
                        self.update_connection(False, "Waiting for client...")
                        self.log("Disconnected from client", "warning")
                    self.reset_state()
                    self.champions_for_role = None
                    _api_instance = None

                time.sleep(0.5)

            except Exception as e:
                self.log(f"Error: {str(e)}", "error")
                time.sleep(1)

    def start(self):
        """Start the bot in a background thread"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the bot"""
        self.running = False
        self.reset_state()
        self.update_connection(False, "Bot stopped")
        self.update_phase("-")
        self.update_role("-")


# Global bot instance
bot = AutoMatchBot()


@eel.expose
def start_bot():
    """Start the bot - called from JavaScript"""
    bot.start()
    eel.setButtonsState(True)


@eel.expose
def stop_bot():
    """Stop the bot - called from JavaScript"""
    bot.stop()
    eel.setButtonsState(False)


@eel.expose
def update_settings(settings: dict):
    """Update bot settings - called from JavaScript"""
    bot.auto_accept = settings.get('auto_accept', True)
    bot.auto_ban = settings.get('auto_ban', True)
    bot.auto_pick = settings.get('auto_pick', True)


@eel.expose
def request_lobby_update():
    """Request lobby data update - called from JavaScript every second on lobby page"""
    global _api_instance, _queues_cache

    try:
        # Try to get API instance
        api = _api_instance

        # If no cached API, try to create one
        if api is None:
            port, token = Client.get_port_and_token()
            if port and token:
                api = Client(port, token)
                _api_instance = api

        if api is None:
            eel.updateLobbyFull({
                'members': [],
                'phase': None,
                'queueName': None
            })
            return

        # Get current phase and queue info
        current_phase = api.get_gameflow_phase()
        session = api.get_session()

        queue_name = None
        if session:
            queue_id = session.get("gameData", {}).get("queue", {}).get("id")
            if queue_id and _queues_cache:
                queue_name = get_current_queue(_queues_cache, queue_id)

        # Get lobby members
        members = api.get_lobby_members()

        if not members:
            eel.updateLobbyFull({
                'members': [],
                'phase': current_phase,
                'queueName': queue_name
            })
            return

        lobby_data = []
        for member in members:
            puuid = member.get("puuid")
            game_name = member.get("gameName", "")
            tag_line = member.get("gameTag", "")

            if not game_name:
                summoner_info = api.get_summoner_by_puuid(puuid)
                if summoner_info:
                    game_name = summoner_info.get("gameName", summoner_info.get("displayName", "Unknown"))
                    tag_line = summoner_info.get("tagLine", "")

            riot_id = f"{game_name}#{tag_line}" if tag_line else game_name

            # Get ranks
            solo_rank_str = "Unranked"
            flex_rank_str = "Unranked"
            ranked_stats = api.get_ranked_stats(puuid)
            if ranked_stats:
                queues = ranked_stats.get("queues", [])
                for queue in queues:
                    queue_type = queue.get("queueType", "")
                    if queue_type == "RANKED_SOLO_5x5":
                        solo_rank_str = _format_rank(queue)
                    elif queue_type == "RANKED_FLEX_SR":
                        flex_rank_str = _format_rank(queue)

            lobby_data.append({
                'name': riot_id,
                'isLeader': member.get("isLeader", False),
                'ready': member.get("ready", False),
                'soloRank': solo_rank_str,
                'flexRank': flex_rank_str
            })

        eel.updateLobbyFull({
            'members': lobby_data,
            'phase': current_phase,
            'queueName': queue_name
        })

    except Exception as e:
        print(f"Error updating lobby: {e}")
        eel.updateLobbyFull({
            'members': [],
            'phase': None,
            'queueName': None
        })


def _format_rank(queue_data):
    """Format rank to readable form"""
    if not queue_data:
        return "Unranked"

    tier = queue_data.get("tier", "")
    division = queue_data.get("division", "")
    lp = queue_data.get("leaguePoints", 0)

    if not tier or tier == "NONE":
        return "Unranked"

    tier_formatted = tier.capitalize()

    if tier in ["CHALLENGER", "GRANDMASTER", "MASTER"]:
        return f"{tier_formatted} {lp} LP"

    return f"{tier_formatted} {division} ({lp} LP)"


@eel.expose
def get_all_presets():
    """Get all presets from database"""
    db = get_presets_db()
    return db.get_all_presets()


@eel.expose
def get_all_champions():
    """Get all available champions from ddragon data"""
    global _ddragon_data_cache

    if _ddragon_data_cache is None:
        _ddragon_data_cache = get_or_download_champions(CHAMPIONS_FILE)

    if not _ddragon_data_cache:
        return []

    champions = []
    data = _ddragon_data_cache.get('data', {})
    for key, champ in data.items():
        champions.append({
            'id': int(champ.get('key', 0)),
            'name': champ.get('name', key),
            'alias': key
        })

    # Sort by name
    champions.sort(key=lambda x: x['name'])
    return champions


@eel.expose
def add_champion_to_preset(role: str, preset_type: str, champion_id: int, champion_name: str):
    """Add champion to preset"""
    db = get_presets_db()
    db.add_champion_to_preset(role, preset_type, champion_id, champion_name)
    bot.reload_presets()


@eel.expose
def remove_champion_from_preset(role: str, preset_type: str, champion_id: int):
    """Remove champion from preset"""
    db = get_presets_db()
    db.remove_champion_from_preset(role, preset_type, champion_id)
    bot.reload_presets()


@eel.expose
def move_champion_in_preset(role: str, preset_type: str, champion_id: int, new_position: int):
    """Move champion to new position in preset"""
    db = get_presets_db()
    db.move_champion(role, preset_type, champion_id, new_position)
    bot.reload_presets()


@eel.expose
def import_presets_from_file():
    """Import presets from config file to database"""
    global _ddragon_data_cache

    if _ddragon_data_cache is None:
        _ddragon_data_cache = get_or_download_champions(CHAMPIONS_FILE)

    champions = load_champions(CONFIG_FILE, BASE_CONFIG_FILE, _ddragon_data_cache)
    db = get_presets_db()
    db.clear_all()
    db.import_from_champions(champions)
    bot.reload_presets()


def run_gui():
    """Initialize and start the Eel application"""
    import os

    # Get the path to the web folder
    web_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'web')

    eel.init(web_folder)

    # Pre-load ddragon data
    global _ddragon_data_cache
    _ddragon_data_cache = get_or_download_champions(CHAMPIONS_FILE)

    # Start the Eel application
    eel.start('index.html', size=(1200, 800), port=0)


if __name__ == '__main__':
    run_gui()
