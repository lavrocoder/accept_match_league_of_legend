from backend.models import Champion


def find_available_champion(preset: list[Champion], unavailable_ids: list[int]) -> Champion | None:
    """Находит первого доступного чемпиона из пресета."""
    for champion in preset:
        if champion.id not in unavailable_ids:
            return champion
    return None