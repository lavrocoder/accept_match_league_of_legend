from app.models import Champions


def get_champions_for_role(champions_for_role_by_mastery, champions: Champions):
    champs = Champions()
    roles = ['top', 'top_ban', 'jungle', 'jungle_ban', 'middle', 'middle_ban',
             'bottom', 'bottom_ban', 'utility', 'utility_ban']

    pick_roles = ['top', 'jungle', 'middle', 'bottom', 'utility']

    for role in roles:
        for champion in getattr(champions, role):
            champion.by = 'выбор'
            getattr(champs, role).append(champion)

    for role in pick_roles:
        for champion in getattr(champions_for_role_by_mastery, role):
            if not champs.exists(role, champion):
                getattr(champs, role).append(champion)

    return champs
