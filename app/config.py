from pathlib import Path

from app.utils import load_or_create_config, get_champions_by_region

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_DIR = BASE_DIR / 'config'
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / 'pick_and_ban_for_roles.txt'
BASE_CONFIG_FILE = BASE_DIR / 'src' / 'pick_and_ban_for_roles.txt'

CHAMPIONS_FILE = DATA_DIR / 'champions.json'