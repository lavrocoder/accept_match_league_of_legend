import json
from pathlib import Path

from backend.clients.ddragon_api import RiotDdragonAPI


def get_or_download_champions(champions_file_path: Path):
    """Скачивает информации о чемпионах текущей версии"""
    api = RiotDdragonAPI()
    if not champions_file_path.exists():  # Если данные ещё не скачаны
        champions = api.get_champions()
        with open(champions_file_path, 'w', encoding='utf-8') as f:
            json.dump(champions, f, ensure_ascii=False, indent=4)
        return champions

    # Проверка соответствия версии
    current_version = api.get_version()
    with open(champions_file_path, 'r', encoding='utf-8') as f:
        champions = json.load(f)

    # Если версии не совпадают, обновляем файл до последней версии
    if current_version != champions.get('version'):
        champions = api.get_champions()
        with open(champions_file_path, 'w', encoding='utf-8') as f:
            json.dump(champions, f, ensure_ascii=False, indent=4)
    return champions

