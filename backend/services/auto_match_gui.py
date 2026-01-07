import eel

from backend.config import CHAMPIONS_FILE, BASE_DIR
from backend.database import init_db
from backend.models.db_models import Setting
from backend.utils import (
    get_or_download_champions
)
from middle.auto_match_bot import AutoMatchBot
from middle.send_to_python import EelForJS


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
