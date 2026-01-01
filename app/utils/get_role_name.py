def get_role_name(current_role):
    """Получает название роли"""
    role_names = {
        "top": "Топ",
        "jungle": "Лес",
        "middle": "Мид",
        "bottom": "АДК",
        "utility": "Саппорт",
    }
    return role_names.get(current_role, current_role)