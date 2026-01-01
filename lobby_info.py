from app.clients.lcu_api import Client

port, token = Client.get_port_and_token()
api = Client(port, token)
members = api.get_lobby_members()

# Собираем информацию о всех участниках
members_info = []

print(f"Участники лобби ({len(members)}):")
print("-" * 40)

for i, member in enumerate(members, 1):
    puuid = member.get("puuid")
    summoner_id = member.get("summonerId")

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

    members_info.append({
        "index": i,
        "puuid": puuid,
        "game_name": game_name,
        "tag_line": tag_line,
        "riot_id": riot_id,
        "is_leader": member.get("isLeader", False)
    })

    print(f"{i}. {is_leader}{riot_id} {is_ready}")