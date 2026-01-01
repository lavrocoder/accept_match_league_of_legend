from app.clients.lcu_api import Client

from app.config import CONFIG_FILE, BASE_CONFIG_FILE, CHAMPIONS_FILE
from app.utils import get_or_download_champions, get_champions_for_role_by_mastery, load_champions, get_current_queue, \
    get_role_name, find_available_champion, print_lobby
from app.utils.get_champions_for_role import get_champions_for_role


def main():
    print("Загрузка героев")
    ddragon_data = get_or_download_champions(CHAMPIONS_FILE)
    champions = load_champions(CONFIG_FILE, BASE_CONFIG_FILE, ddragon_data)

    match_accepted = False
    is_port_printed = False
    last_phase = None
    current_role = None
    role_printed = False
    champions_for_role = None
    ban_completed = False
    pick_completed = False
    queues = []

    while True:
        port, token = Client.get_port_and_token()
        if port and token:
            api = Client(port, token)
            if not is_port_printed:
                print(f"Подключено к клиенту")
                is_port_printed = True
                mastery = api.get_champions_mastery()
                recommended_positions = api.get_recommended_champion_positions()
                champions_for_role_by_mastery = get_champions_for_role_by_mastery(ddragon_data, mastery,
                                                                                  recommended_positions)
                champions_for_role = get_champions_for_role(champions_for_role_by_mastery, champions)
                champions_for_role.print_table()

                queues = api.get_queues()

            # region Логируем смену фазы
            current_phase = api.get_gameflow_phase()
            session = api.get_session()
            queue_id = session.get("gameData", {}).get("queue", {}).get("id")
            queue_name = get_current_queue(queues, queue_id)

            current_phase_name = f"{current_phase} - {queue_name}"
            if current_phase_name != last_phase:
                if current_phase:
                    print(f"📍 Фаза: {current_phase_name}")
                    if current_phase == 'Matchmaking':
                        print_lobby(api)
                last_phase = current_phase_name
                # Сбрасываем флаги при смене фазы
                if current_phase != "ChampSelect":
                    ban_completed = False
                    pick_completed = False
                    current_role = None
                    role_printed = False
            # endregion

            # region Проверяем, найден ли матч
            if current_phase == "ReadyCheck":
                ready_check = api.check_match_found()

                if ready_check and not match_accepted:
                    player_response = ready_check.get("playerResponse", "None")

                    # Принимаем только если ещё не приняли
                    if player_response == "None":
                        print(f"🎮 Матч найден! Режим: {queue_name}")
                        if api.accept_match():
                            print("✅ Матч автоматически принят!")
                            match_accepted = True
                        else:
                            print("❌ Ошибка при принятии матча")
                    elif player_response == "Accepted":
                        match_accepted = True
            else:
                match_accepted = False

            # region Обработка выбора чемпионов
            if current_phase == "ChampSelect":
                # Получаем роль, если ещё не получили
                if current_role is None:
                    current_role = api.get_my_assigned_role()

                pick_preset, ban_preset = champions_for_role.get_presets_for_role(current_role)
                # Выводим информацию о роли один раз
                if not role_printed and current_role:
                    role_name = get_role_name(current_role)
                    print(f"👤 Роль: {role_name}")
                    print(f"📋 Баны: {', '.join([unit.name for unit in ban_preset[:10]])}")
                    print(f"📋 Пики: {', '.join([unit.name for unit in pick_preset[:10]])}")
                    role_printed = True
                # elif not role_printed and current_role is None:
                #     # Роль не назначена (ARAM, слепой выбор и т.д.)
                #     print(f"📋 Баны: {', '.join(BAN_PRESET_DEFAULT)}")
                #     print(f"📋 Пики: {', '.join(PICK_PRESET_DEFAULT)}")
                #     role_printed = True

                # Получаем пресеты для текущей роли
                phase_info = api.get_phase_info()
                if not ban_completed:
                    if phase_info and phase_info.get('phase') == 'BAN_PICK' and phase_info.get(
                            'current_action_type') == 'ban':
                        ban_action_id = phase_info.get('action_id')
                        banned = api.get_banned_champions()
                        champ = find_available_champion(ban_preset, banned)

                        if champ:
                            print(f"🚫 Баним: {champ.name}")
                            if api.perform_action(ban_action_id, champ.id, complete=True):
                                print(f"✅ {champ.name} забанен!")
                                ban_completed = True
                            else:
                                print(f"❌ Ошибка при бане {champ.name}")
                        else:
                            print("⚠️ Нет доступных чемпионов для бана из пресета")
                            ban_completed = True

                # Проверяем фазу пика
                if not pick_completed:
                    if phase_info and phase_info.get('phase') == 'BAN_PICK' and phase_info.get(
                            'current_action_type') == 'pick' and phase_info.get('is_my_turn'):
                        pick_action_id = phase_info.get('action_id')
                        banned = api.get_banned_champions()
                        picked = api.get_picked_champions()
                        unavailable = banned | picked

                        champ = find_available_champion(pick_preset, unavailable)

                        if champ:
                            print(f"🎯 Пикаем: {champ.name}")
                            if api.perform_action(pick_action_id, champ.id, complete=True):
                                print(f"✅ {champ.name} выбран!")
                                pick_completed = True
                            else:
                                print(f"❌ Ошибка при пике {champ.name}")
                        else:
                            print("⚠️ Нет доступных чемпионов для пика из пресета")
                            pick_completed = True

        else:
            match_accepted = False
            is_port_printed = False
            last_phase = None
            current_role = None
            role_printed = False
            champions_for_role = None
            ban_completed = False
            pick_completed = False
            queues = []

if __name__ == '__main__':
    main()