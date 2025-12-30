import json
from pprint import pprint

from app.clients.lcu_api import LcuApi, Client

from app.config import CONFIG_FILE, BASE_CONFIG_FILE, CHAMPIONS_FILE
from app.utils import get_or_download_champions, get_champions_for_role_by_mastery, load_champions
from app.utils.get_champions_for_role import get_champions_for_role


def main():
    print("Загрузка героев")
    ddragon_data = get_or_download_champions(CHAMPIONS_FILE)
    champions = load_champions(CONFIG_FILE, BASE_CONFIG_FILE, ddragon_data)
    port, token = Client.get_port_and_token()
    api = Client(port, token)
    mastery = api.get_champions_mastery()
    recommended_positions = api.get_recommended_champion_positions()
    champions_for_role_by_mastery = get_champions_for_role_by_mastery(ddragon_data, mastery, recommended_positions)
    champions_for_role = get_champions_for_role(champions_for_role_by_mastery, champions)
    print("Топ")
    for champion in champions_for_role.top:
        print(champion)
    print("Лес")
    for champion in champions_for_role.jungle:
        print(champion)
    print("Мид")
    for champion in champions_for_role.middle:
        print(champion)
    print("Бот")
    for champion in champions_for_role.bottom:
        print(champion)
    print("Саппорт")
    for champion in champions_for_role.utility:
        print(champion)
    # mastery = api.get_champions_for_role_by_mastery()
    # pprint(mastery)



if __name__ == '__main__':
    main()