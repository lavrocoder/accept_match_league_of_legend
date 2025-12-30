from pathlib import Path

from app.models import Champions
from app.utils import load_or_create_config, get_champions_by_region
from app.utils.find_champion_by_name import find_champion_by_name


def load_champions(file_path: Path, base_file_path: Path, ddragon_data) -> Champions:
    champs = Champions()
    config_text = load_or_create_config(file_path, base_file_path)

    champions = get_champions_by_region('Топ (пик)', config_text)
    for champion in champions:
        champ = find_champion_by_name(ddragon_data, champion)
        if champ is None:
            print(f"Чемпион '{champion}' не найден")
        else:
            champs.top.append(champ)

    champions = get_champions_by_region('Топ (бан)', config_text)
    for champion in champions:
        champ = find_champion_by_name(ddragon_data, champion)
        if champ is None:
            print(f"Чемпион '{champion}' не найден")
        else:
            champs.top_ban.append(champ)

    champions = get_champions_by_region('Лес (пик)', config_text)
    for champion in champions:
        champ = find_champion_by_name(ddragon_data, champion)
        if champ is None:
            print(f"Чемпион '{champion}' не найден")
        else:
            champs.jungle.append(champ)

    champions = get_champions_by_region('Лес (бан)', config_text)
    for champion in champions:
        champ = find_champion_by_name(ddragon_data, champion)
        if champ is None:
            print(f"Чемпион '{champion}' не найден")
        else:
            champs.jungle_ban.append(champ)

    champions = get_champions_by_region('Мид (пик)', config_text)
    for champion in champions:
        champ = find_champion_by_name(ddragon_data, champion)
        if champ is None:
            print(f"Чемпион '{champion}' не найден")
        else:
            champs.middle.append(champ)

    champions = get_champions_by_region('Мид (бан)', config_text)
    for champion in champions:
        champ = find_champion_by_name(ddragon_data, champion)
        if champ is None:
            print(f"Чемпион '{champion}' не найден")
        else:
            champs.middle_ban.append(champ)

    champions = get_champions_by_region('Бот (пик)', config_text)
    for champion in champions:
        champ = find_champion_by_name(ddragon_data, champion)
        if champ is None:
            print(f"Чемпион '{champion}' не найден")
        else:
            champs.bottom.append(champ)

    champions = get_champions_by_region('Бот (бан)', config_text)
    for champion in champions:
        champ = find_champion_by_name(ddragon_data, champion)
        if champ is None:
            print(f"Чемпион '{champion}' не найден")
        else:
            champs.bottom_ban.append(champ)

    champions = get_champions_by_region('Саппорт (пик)', config_text)
    for champion in champions:
        champ = find_champion_by_name(ddragon_data, champion)
        if champ is None:
            print(f"Чемпион '{champion}' не найден")
        else:
            champs.utility.append(champ)

    champions = get_champions_by_region('Саппорт (бан)', config_text)
    for champion in champions:
        champ = find_champion_by_name(ddragon_data, champion)
        if champ is None:
            print(f"Чемпион '{champion}' не найден")
        else:
            champs.utility_ban.append(champ)

    return champs
