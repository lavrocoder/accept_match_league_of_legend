from app.utils import format_rank


def get_lobby(api) -> list[dict]:
    members = api.get_lobby_members()
    if not members:
        return []
    lobby_data = []
    for member in members:
        puuid = member.get("puuid")
        game_name = member.get("gameName", "")
        tag_line = member.get("gameTag", "")

        if not game_name:
            summoner_info = api.get_summoner_by_puuid(puuid)
            if summoner_info:
                game_name = summoner_info.get("gameName", summoner_info.get("displayName", "Unknown"))
                tag_line = summoner_info.get("tagLine", "")

        riot_id = f"{game_name}#{tag_line}" if tag_line else game_name

        # Get ranks
        solo_rank_str = "Unranked"
        flex_rank_str = "Unranked"
        ranked_stats = api.get_ranked_stats(puuid)
        if ranked_stats:
            queues = ranked_stats.get("queues", [])
            for queue in queues:
                queue_type = queue.get("queueType", "")
                if queue_type == "RANKED_SOLO_5x5":
                    solo_rank_str = format_rank(queue)
                elif queue_type == "RANKED_FLEX_SR":
                    flex_rank_str = format_rank(queue)

        lobby_data.append({
            'name': riot_id,
            'isLeader': member.get("isLeader", False),
            'ready': member.get("ready", False),
            'soloRank': solo_rank_str,
            'flexRank': flex_rank_str
        })
    return lobby_data