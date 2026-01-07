def format_rank(queue_data: dict):
    """Format rank to readable form"""
    if not queue_data:
        return "Unranked"

    tier = queue_data.get("tier", "")
    division = queue_data.get("division", "")
    lp = queue_data.get("leaguePoints", 0)

    if not tier or tier == "NONE":
        return "Unranked"

    tier_formatted = tier.capitalize()

    if tier in ["CHALLENGER", "GRANDMASTER", "MASTER"]:
        return f"{tier_formatted} {lp} LP"

    return f"{tier_formatted} {division} ({lp} LP)"