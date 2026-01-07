def get_champions_by_region(region, text):
    champions = []
    in_progress = False
    for line in text.split('\n'):
        if line.startswith(f'# region {region}'):
            in_progress = True
        elif line.startswith(f'# endregion {region}'):
            break
        elif in_progress:
            champion = line.strip()
            if champion != '' and champion.lower() not in champions:
                champions.append(champion)
    return champions