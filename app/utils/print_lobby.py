def format_rank(queue_data):
    """Форматирует ранг в читаемый вид."""
    if not queue_data:
        return "Unranked"

    tier = queue_data.get("tier", "")
    division = queue_data.get("division", "")
    lp = queue_data.get("leaguePoints", 0)

    if not tier or tier == "NONE":
        return "Unranked"

    # Форматируем tier с заглавной буквы
    tier_formatted = tier.capitalize()

    # Для Challenger, Grandmaster, Master не показываем дивизию
    if tier in ["CHALLENGER", "GRANDMASTER", "MASTER"]:
        return f"{tier_formatted} {lp} LP"

    return f"{tier_formatted} {division} ({lp} LP)"


def get_player_ranks(api, puuid):
    """Получает ранги игрока (соло/дуо и гибкий)."""
    ranked_stats = api.get_ranked_stats(puuid)

    if not ranked_stats:
        return None, None

    queues = ranked_stats.get("queues", [])

    solo_rank = None
    flex_rank = None

    for queue in queues:
        queue_type = queue.get("queueType", "")
        if queue_type == "RANKED_SOLO_5x5":
            solo_rank = queue
        elif queue_type == "RANKED_FLEX_SR":
            flex_rank = queue

    return solo_rank, flex_rank


def print_lobby(api):
    """Выводит информацию об участниках лобби с рангами."""
    members = api.get_lobby_members()

    if not members:
        print("Лобби пустое или недоступно")
        return

    print(f"\n📋 Участники лобби ({len(members)}):")
    print("-" * 60)

    for i, member in enumerate(members, 1):
        puuid = member.get("puuid")

        # Получаем Riot ID из gameName и tagLine
        game_name = member.get("gameName", "")
        tag_line = member.get("gameTag", "")

        # Если нет в member, пробуем получить через summoner API
        if not game_name:
            summoner_info = api.get_summoner_by_puuid(puuid)
            if summoner_info:
                game_name = summoner_info.get("gameName", summoner_info.get("displayName", "Unknown"))
                tag_line = summoner_info.get("tagLine", "")

        riot_id = f"{game_name}#{tag_line}" if tag_line else game_name

        is_leader = "👑 " if member.get("isLeader") else ""
        is_ready = "✅" if member.get("ready") else "⏳"

        # Получаем ранги
        solo_rank, flex_rank = get_player_ranks(api, puuid)
        solo_rank_str = format_rank(solo_rank)
        flex_rank_str = format_rank(flex_rank)

        print(f"{i}. {is_leader}{riot_id} {is_ready}")
        print(f"   Соло/Дуо: {solo_rank_str}")
        print(f"   Гибкий:   {flex_rank_str}")

    print("-" * 60)
