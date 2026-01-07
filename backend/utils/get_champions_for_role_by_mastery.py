from backend.models import Champion, ChampionsByRoleAndMastery

def get_champion_level_and_points(mastery: list[dict], champion_id: int) -> tuple[int, int]:
    for item in mastery:
        if item['championId'] == champion_id:
            return item['championLevel'], item['championPoints']
    return 0, 0



def get_champions_for_role_by_mastery(ddragon_data, mastery, recommended_positions) -> ChampionsByRoleAndMastery:
    champions = ChampionsByRoleAndMastery()
    for key, value in ddragon_data['data'].items():
        champion_id = int(value['key'])
        level, points = get_champion_level_and_points(mastery, champion_id)
        champion = Champion(id=champion_id, name=value['name'], alias=value['id'], level=level, points=points)
        positions = recommended_positions.get(str(champion.id), {}).get('recommendedPositions', [])
        for position in positions:
            if position == 'TOP':
                champions.top.append(champion)
            elif position == 'JUNGLE':
                champions.jungle.append(champion)
            elif position == 'MIDDLE':
                champions.middle.append(champion)
            elif position == 'BOTTOM':
                champions.bottom.append(champion)
            elif position == 'UTILITY':
                champions.utility.append(champion)
    champions.sort_by_mastery()
    return champions