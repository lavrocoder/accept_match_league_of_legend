from backend.models import Champion


def normolize_name(name):
    name = name.lower()
    name = name.replace("'", '')
    return name


def find_champion_by_name(ddragon_data, name: str) -> Champion | None:
    """
    Ищет чемпиона по имени русскому или английскому. Игнорирует символ "'".
    :param ddragon_data:
    :param name:
    :return:
    """
    for champion in ddragon_data['data'].values():
        if normolize_name(champion['name']) == normolize_name(name):
            return Champion(id=int(champion['key']), name=champion['name'], alias=champion['id'], level=0, points=0)
        if normolize_name(champion['id']) == normolize_name(name):
            return Champion(id=int(champion['key']), name=champion['name'], alias=champion['id'], level=0, points=0)
    return None