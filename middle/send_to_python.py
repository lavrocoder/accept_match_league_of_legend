from backend.config import CONFIG_FILE, BASE_CONFIG_FILE
from backend.models.db_models import Setting, Preset
from backend.utils import get_lobby, get_current_queue, load_champions
from middle.auto_match_bot import AutoMatchBot


class EelForJS:
    def __init__(self, bot: AutoMatchBot, ddragon_data):
        self.bot = bot
        self.ddragon_data = ddragon_data

    def start_bot(self):
        """Start the bot - called from JavaScript"""
        self.bot.start()
        self.bot.eel.set_buttons_state(True)

    def stop_bot(self):
        """Stop the bot - called from JavaScript"""
        self.bot.stop()
        self.bot.eel.set_buttons_state(False)

    @staticmethod
    def get_all_presets():
        """Get all presets from database"""
        return Preset.get_all_presets()

    def get_all_champions(self):
        """Get all available champions from ddragon data"""

        if not self.ddragon_data:
            return []

        champions = []
        data = self.ddragon_data.get('data', {})
        for key, champ in data.items():
            champions.append({
                'id': int(champ.get('key', 0)),
                'name': champ.get('name', key),
                'alias': key
            })

        # Sort by name
        champions.sort(key=lambda x: x['name'])
        return champions

    @staticmethod
    def get_settings():
        """Get settings from database - called from JavaScript"""
        return Setting.get_all_settings()

    def update_settings(self, settings: dict):
        """Update bot settings - called from JavaScript"""

        self.bot.auto_accept = settings.get('auto_accept', True)
        self.bot.auto_ban = settings.get('auto_ban', True)
        self.bot.auto_pick = settings.get('auto_pick', True)

        # Save to database
        Setting.set_setting('auto_accept', self.bot.auto_accept)
        Setting.set_setting('auto_ban', self.bot.auto_ban)
        Setting.set_setting('auto_pick', self.bot.auto_pick)

    def request_lobby_update(self):
        """Request lobby data update - called from JavaScript every second on lobby page"""
        try:
            if self.bot.api is None:
                self.bot.eel.update_lobby_full([], None, None)
                return

            # Get current phase and queue info
            current_phase = self.bot.api.get_gameflow_phase()
            session = self.bot.api.get_session()

            queue_name = None
            if session:
                queue_id = session.get("gameData", {}).get("queue", {}).get("id")
                if queue_id and self.bot.queues:
                    queue_name = get_current_queue(self.bot.queues, queue_id)

            lobby_data = get_lobby(self.bot.api)
            if not lobby_data:
                self.bot.eel.update_lobby_full([], current_phase, queue_name)

            self.bot.eel.update_lobby_full(lobby_data, current_phase, queue_name)

        except Exception as e:
            print(f"Error updating lobby: {e}")
            self.bot.eel.update_lobby_full([], None, None)

    def import_presets_from_file(self):
        """Import presets from config file to database"""
        champions = load_champions(CONFIG_FILE, BASE_CONFIG_FILE, self.ddragon_data)
        Preset.clear_all()
        Preset.import_from_champions(champions)
        self.bot.reload_presets()

    def add_champion_to_preset(self, role: str, preset_type: str, champion_id: int, champion_name: str):
        """Add champion to preset"""
        Preset.add_champion_to_preset(role, preset_type, champion_id, champion_name)
        self.bot.reload_presets()

    def remove_champion_from_preset(self, role: str, preset_type: str, champion_id: int):
        """Remove champion from preset"""
        Preset.remove_champion_from_preset(role, preset_type, champion_id)
        self.bot.reload_presets()

    def move_champion_in_preset(self, role: str, preset_type: str, champion_id: int, new_position: int):
        """Move champion to new position in preset"""
        Preset.move_champion(role, preset_type, champion_id, new_position)
        self.bot.reload_presets()
