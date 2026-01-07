import threading
import time
from typing import Optional

import eel

from backend.clients.lcu_api import Client
from backend.config import CONFIG_FILE, BASE_CONFIG_FILE, CHAMPIONS_FILE, BASE_DIR
from backend.database import init_db
from backend.models.db_models import Setting, Preset
from backend.models.schemas import Champions, Champion
from backend.services.updater import ProjectUpdater
from backend.utils import (
    get_or_download_champions,
    get_champions_for_role_by_mastery,
    load_champions,
    get_current_queue,
    get_role_name,
    find_available_champion, get_lobby
)
from backend.utils.get_champions_for_role import get_champions_for_role
from middle.send_to_js import Eel
from middle.send_to_python import EelForJS


class AutoMatchBot:
    def __init__(self, ddragon_data):
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Settings
        self.auto_accept = True
        self.auto_ban = True
        self.auto_pick = True

        # State
        self.is_connected = False
        self.last_phase = None
        self.current_role = None
        self.role_printed = False
        self.champions_for_role: Optional[Champions] = None
        self.ban_completed = False
        self.pick_completed = False

        # Data
        self.ddragon_data = ddragon_data
        self.champions = None
        self.queues = []

        self.eel = Eel()
        self.api: Client | None = None

    def update_connection(self, connected: bool, text: str):
        """Update connection status in UI"""
        self.eel.update_connection(connected, text)
        self.is_connected = connected

    def update_lobby(self, api):
        """Send lobby members to UI"""
        lobby = get_lobby(api)
        self.eel.update_lobby(lobby)

    def reset_state(self):
        """Reset bot state"""
        self.last_phase = None
        self.current_role = None
        self.role_printed = False
        self.ban_completed = False
        self.pick_completed = False
        self.queues = []

    def load_data(self):
        """Load champion data"""
        self.eel.log("Loading champions...", "info")

        # Load presets from database
        if Preset.is_empty():
            # Import from file if database is empty
            self.champions = load_champions(CONFIG_FILE, BASE_CONFIG_FILE, self.ddragon_data)
            Preset.import_from_champions(self.champions)
            self.eel.log("Presets imported to database", "info")
        else:
            # Load from database
            self.champions = self._load_champions_from_db()
        self.eel.log("Presets loaded", "success")

        # Load settings from database
        self.auto_accept = Setting.get_setting('auto_accept')
        self.auto_ban = Setting.get_setting('auto_ban')
        self.auto_pick = Setting.get_setting('auto_pick')

    @staticmethod
    def _load_champions_from_db() -> Champions:
        """Load champions from database into Champions model"""
        presets = Preset.get_all_presets()
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
        champions_for_role_by_mastery = None
        updater = ProjectUpdater()
        updater.check_for_updates()

        self.load_data()
        self.update_connection(False, "Waiting for client...")

        while self.running:
            try:
                port, token = Client.get_port_and_token()

                if port and token:
                    self.api = Client(port, token)

                    if not self.is_connected:
                        mastery = self.api.get_champions_mastery()
                        if mastery:
                            self.update_connection(True, "Connected to client")
                            self.eel.log("Connected to client", "success")

                            recommended_positions = self.api.get_recommended_champion_positions()
                            champions_for_role_by_mastery = get_champions_for_role_by_mastery(
                                self.ddragon_data, mastery, recommended_positions
                            )
                            self.champions_for_role = get_champions_for_role(
                                champions_for_role_by_mastery, self.champions
                            )
                            self.eel.update_champions_table(self.champions_for_role)
                            self.queues = self.api.get_queues()

                    # Get current phase
                    current_phase = self.api.get_gameflow_phase()
                    session = self.api.get_session()

                    if session is None:
                        time.sleep(0.5)
                        continue

                    queue_id = session.get("gameData", {}).get("queue", {}).get("id")
                    queue_name = get_current_queue(self.queues, queue_id)

                    current_phase_name = f"{current_phase} - {queue_name}" if queue_name else current_phase

                    if current_phase_name != self.last_phase:
                        if current_phase:
                            self.eel.log(f"Phase: {current_phase_name}", "phase")
                            self.eel.update_phase(current_phase_name)

                            if current_phase == 'Matchmaking':
                                self.update_lobby(self.api)

                        self.last_phase = current_phase_name

                        if current_phase != "ChampSelect":
                            self.ban_completed = False
                            self.pick_completed = False
                            self.current_role = None
                            self.role_printed = False
                            self.eel.update_role("-")

                    # Handle match found
                    if current_phase == "ReadyCheck" and self.auto_accept:
                        ready_check = self.api.check_match_found()

                        if ready_check:
                            player_response = ready_check.get("playerResponse", "None")

                            if player_response == "None":
                                self.eel.log(f"Match found! Mode: {queue_name}", "warning")
                                if self.api.accept_match():
                                    self.eel.log("Match accepted!", "success")
                                else:
                                    self.eel.log("Failed to accept match", "error")

                    # Handle champion select
                    if current_phase == "ChampSelect":
                        if self.current_role is None:
                            self.current_role = self.api.get_my_assigned_role()

                        if self.champions_for_role:
                            pick_preset, ban_preset = self.champions_for_role.get_presets_for_role(
                                self.current_role
                            )

                            if not self.role_printed and self.current_role:
                                role_name = get_role_name(self.current_role)
                                self.eel.log(f"Role: {role_name}", "info")
                                self.eel.update_role(role_name)

                                ban_names = ', '.join([unit.name for unit in ban_preset[:10]])
                                pick_names = ', '.join([unit.name for unit in pick_preset[:10]])
                                self.eel.log(f"Bans: {ban_names}", "info")
                                self.eel.log(f"Picks: {pick_names}", "info")
                                self.role_printed = True

                            phase_info = self.api.get_phase_info()

                            # Handle ban phase
                            if not self.ban_completed and self.auto_ban:
                                if (phase_info and
                                        phase_info.get('phase') == 'BAN_PICK' and
                                        phase_info.get('current_action_type') == 'ban'):

                                    # Reload ban preset from database
                                    self.reload_presets()
                                    self.champions_for_role = get_champions_for_role(
                                        champions_for_role_by_mastery, self.champions
                                    )
                                    _, ban_preset = self.champions_for_role.get_presets_for_role(
                                        self.current_role
                                    )

                                    ban_action_id = phase_info.get('action_id')
                                    banned = self.api.get_banned_champions()
                                    champ = find_available_champion(ban_preset, banned)

                                    if champ:
                                        self.eel.log(f"Banning: {champ.name}", "info")
                                        if self.api.perform_action(ban_action_id, champ.id, complete=True):
                                            self.eel.log(f"{champ.name} banned!", "success")
                                            self.ban_completed = True
                                        else:
                                            self.eel.log(f"Failed to ban {champ.name}", "error")
                                    else:
                                        self.eel.log("No available champions for ban from preset", "warning")
                                        self.ban_completed = True

                            # Handle pick phase
                            if not self.pick_completed and self.auto_pick:
                                if (phase_info and
                                        phase_info.get('phase') == 'BAN_PICK' and
                                        phase_info.get('current_action_type') == 'pick' and
                                        phase_info.get('is_my_turn')):

                                    # Reload pick preset from database
                                    self.reload_presets()
                                    self.champions_for_role = get_champions_for_role(
                                        champions_for_role_by_mastery, self.champions
                                    )
                                    pick_preset, _ = self.champions_for_role.get_presets_for_role(
                                        self.current_role
                                    )

                                    pick_action_id = phase_info.get('action_id')
                                    banned = self.api.get_banned_champions()
                                    picked = self.api.get_picked_champions()
                                    unavailable = banned | picked

                                    champ = find_available_champion(pick_preset, unavailable)

                                    if champ:
                                        self.eel.log(f"Picking: {champ.name}", "info")
                                        if self.api.perform_action(pick_action_id, champ.id, complete=True):
                                            self.eel.log(f"{champ.name} picked!", "success")
                                            self.pick_completed = True
                                        else:
                                            self.eel.log(f"Failed to pick {champ.name}", "error")
                                    else:
                                        self.eel.log("No available champions for pick from preset", "warning")
                                        self.pick_completed = True

                else:
                    if self.is_connected:
                        self.update_connection(False, "Waiting for client...")
                        self.eel.log("Disconnected from client", "warning")
                    self.reset_state()
                    self.champions_for_role = None

                time.sleep(0.5)

            except Exception as e:
                self.eel.log(f"Error: {str(e)}", "error")
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
        self.eel.update_phase("-")
        self.eel.update_role("-")


def run_gui():
    """Initialize and start the Eel application"""
    web_folder = BASE_DIR / 'frontend'
    init_db()
    Setting.init_default_settings()
    Setting.get_all_settings()

    ddragon_data = get_or_download_champions(CHAMPIONS_FILE)
    bot = AutoMatchBot(ddragon_data)

    eel_from_js = EelForJS(bot, ddragon_data)
    eel.expose(eel_from_js.start_bot)
    eel.expose(eel_from_js.stop_bot)
    eel.expose(eel_from_js.get_all_presets)
    eel.expose(eel_from_js.get_all_champions)
    eel.expose(eel_from_js.get_settings)
    eel.expose(eel_from_js.update_settings)
    eel.expose(eel_from_js.request_lobby_update)
    eel.expose(eel_from_js.import_presets_from_file)
    eel.expose(eel_from_js.add_champion_to_preset)
    eel.expose(eel_from_js.remove_champion_from_preset)
    eel.expose(eel_from_js.move_champion_in_preset)
    eel.init(web_folder)

    # Start the Eel application
    eel.start('index.html', size=(1200, 800), port=0)


if __name__ == '__main__':
    run_gui()
