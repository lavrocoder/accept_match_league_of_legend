import base64
import re
import subprocess

import requests
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LcuApi(object):
    def __init__(self, port, token):
        self.port = port
        self.token = token
        self.headers = self._get_lcu_headers()

    def _get_lcu_headers(self):
        """Создает заголовки для LCU API."""
        auth_string = f"riot:{self.token}"
        auth_bytes = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        return {
            "Authorization": f"Basic {auth_bytes}",
            "Accept": "application/json"
        }

    @classmethod
    def get_port_and_token(cls) -> tuple[int | None, str | None]:
        """Получает данные из lockfile клиента League of Legends."""
        try:
            ps_command = (
                "Get-CimInstance Win32_Process -Filter \"name='LeagueClientUx.exe'\" | "
                "Select-Object -ExpandProperty CommandLine"
            )
            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )

            command_line = result.stdout

            port_match = re.search(r'--app-port=(\d+)', command_line)
            token_match = re.search(r'--remoting-auth-token=([\w-]+)', command_line)

            if port_match and token_match:
                port = port_match.group(1)
                token = token_match.group(1)
                return port, token

            return None, None
        except Exception as e:
            print(f"Ошибка при получении данных lockfile: {e}")
            return None, None

    def lcu_request(self, endpoint, method="GET"):
        """Выполняет запрос к LCU API."""
        url = f"https://127.0.0.1:{self.port}{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, verify=False, timeout=5)
            else:
                response = requests.post(url, headers=self.headers, verify=False, timeout=5)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return True
            return None
        except requests.exceptions.RequestException:
            return None

    def get_queues(self):
        """Получает все когда-либо добавленные очереди в игре"""
        queues = self.lcu_request('/lol-game-queues/v1/queues')
        return queues

    def get_recommended_champion_positions(self):
        """Получает рекомендуемые позиции для чемпионов"""
        return self.lcu_request('/lol-perks/v1/recommended-champion-positions')

    def get_champions_mastery(self):
        """Получает мастерство чемпионов текущего пользователя"""
        return self.lcu_request('/lol-champion-mastery/v1/local-player/champion-mastery')

    def get_champions(self):
        return self.lcu_request('/lol-champions/v1/owned-champions-minimal')

    def get_gameflow_phase(self):
        url = f"https://127.0.0.1:{self.port}/lol-gameflow/v1/gameflow-phase"

        try:
            response = requests.get(url, headers=self.headers, verify=False, timeout=5)
            if response.status_code == 200:
                return response.text.strip('"')
            return None
        except requests.exceptions.RequestException:
            return None

    def get_session(self):
        return self.lcu_request('/lol-gameflow/v1/session')

    def check_match_found(self):
        """Проверяет, найден ли матч через LCU API."""
        data = self.lcu_request("/lol-matchmaking/v1/ready-check")
        if data and data.get("state") in ["InProgress", "EveryoneReady"]:
            return data
        return None

    def accept_match(self):
        """Принимает матч через LCU API."""
        result = self.lcu_request("/lol-matchmaking/v1/ready-check/accept", "POST")
        return result is not None

    def get_champ_select_session(self):
        """Получает информацию о сессии выбора чемпионов."""
        return self.lcu_request("/lol-champ-select/v1/session")

    def get_my_assigned_role(self):
        """Получает назначенную роль игрока в текущей сессии."""
        data = self.get_champ_select_session()
        if not data:
            return None

        local_player_cell_id = data.get("localPlayerCellId")
        my_team = data.get("myTeam", [])

        for player in my_team:
            if player.get("cellId") == local_player_cell_id:
                # assignedPosition может быть: top, jungle, middle, bottom, utility
                return player.get("assignedPosition")

        return None

    def get_lobby_members(self):
        """Получает список участников лобби."""
        data = self.lcu_request("/lol-lobby/v2/lobby")
        if data:
            return data.get("members", [])
        return []

    def get_summoner_by_puuid(self, puuid):
        """Получает информацию о саммонере по PUUID."""
        return self.lcu_request(f"/lol-summoner/v2/summoners/puuid/{puuid}")


class Client(LcuApi):
    def get_queues(self):
        queues = super().get_queues()
        id_name = []
        for queue in queues:
            id_name.append(
                {
                    'id': queue['id'],
                    'name': queue['name'],
                }
            )
        id_name.sort(key=lambda x: x['id'])
        return id_name

    @staticmethod
    def get_my_action(data, action_type):
        """Получает текущее действие игрока (ban или pick)."""
        if not data:
            return None, None

        local_player_cell_id = data.get("localPlayerCellId")
        actions = data.get("actions", [])

        for action_group in actions:
            for action in action_group:
                if (action.get("actorCellId") == local_player_cell_id and
                        action.get("isInProgress") and
                        action.get("type") == action_type and
                        not action.get("completed")):
                    return action.get("id"), action

        return None, None

    def get_phase_info(self):
        """Получает информацию о сессии выбора чемпионов."""

        action_types = {
            "ban": "Бан",
            "pick": "Пик",
            "ten_bans_reveal": "Показ банов",
        }

        champ_select_phases = {
            "PLANNING": "Препик",
            "BAN_PICK": "Баны/Пики",
            "FINALIZATION": "Подготовка к матчу",
        }
        data = self.get_champ_select_session()
        if data:
            timer = data.get("timer", {})
            phase = timer.get("phase", "UNKNOWN")
            phase_name = champ_select_phases.get(phase, phase)

            # Информация о локальном игроке
            local_player_cell_id = data.get("localPlayerCellId")
            my_team = data.get("myTeam", [])

            local_player = None
            for player in my_team:
                if player.get("cellId") == local_player_cell_id:
                    local_player = player
                    break

            # Информация о банах
            bans = data.get("bans", {})
            my_team_bans = bans.get("myTeamBans", [])
            their_team_bans = bans.get("theirTeamBans", [])

            # Анализ действий для определения текущей фазы
            actions = data.get("actions", [])

            current_action = None
            current_action_is_mine = False
            action_type = None
            action_status = None  # "my_turn", "waiting", "completed"

            # Определяем общую фазу действий (бан или пик) и статус
            all_actions_completed = True
            current_phase_type = None  # "ban" или "pick"

            my_active_action = None  # Моё активное действие (если есть)

            for action_group in actions:
                for action in action_group:
                    actor_cell_id = action.get("actorCellId")
                    is_my_action = actor_cell_id == local_player_cell_id
                    is_completed = action.get("completed", False)
                    is_in_progress = action.get("isInProgress", False)
                    act_type = action.get("type")

                    if not is_completed:
                        all_actions_completed = False
                        current_phase_type = act_type

                    if is_in_progress:
                        # Запоминаем любое активное действие
                        if current_action is None:
                            current_action = action
                            action_type = act_type

                        # Если это моё действие - запоминаем его отдельно
                        if is_my_action:
                            my_active_action = action
                            current_action_is_mine = True
                            action_status = "my_turn"

            # Если есть моё активное действие, используем его как текущее
            if my_active_action:
                current_action = my_active_action
            elif current_action:
                # Есть активное действие, но не моё
                action_status = "waiting"

            # Если нет активного действия, но есть незавершённые — ожидание
            if not current_action and not all_actions_completed:
                action_status = "waiting_others"
                action_type = current_phase_type

            # Формируем понятное описание текущего действия
            action_description = None
            if phase == "PLANNING":
                action_description = "Препик (выбор намерения)"
            elif phase == "FINALIZATION":
                action_description = "Подготовка к матчу (выбор рун/скинов)"
            elif action_type:
                action_type_name = action_types.get(action_type, action_type)
                if action_status == "my_turn":
                    action_description = f"Ваш {action_type_name}!"
                elif action_status == "waiting":
                    action_description = f"Ожидание {action_type_name}а других игроков"
                elif action_status == "waiting_others":
                    action_description = f"Ожидание {action_type_name}а оставшихся игроков"

            action_id, _ = self.get_my_action(data, action_type)

            return {
                "action_id": action_id,
                "phase": phase,
                "phase_name": phase_name,
                "local_player": local_player,
                "my_team_bans": my_team_bans,
                "their_team_bans": their_team_bans,
                "current_action_type": action_type,
                "action_status": action_status,
                "action_description": action_description,
                "is_my_turn": current_action_is_mine,
                "time_remaining": timer.get("adjustedTimeLeftInPhase", 0) // 1000,
            }
        return None

    def get_banned_champions(self):
        """Получает список уже забаненных чемпионов."""
        data = self.get_champ_select_session()
        if not data:
            return set()

        banned = set()
        bans = data.get("bans", {})
        banned.update(bans.get("myTeamBans", []))
        banned.update(bans.get("theirTeamBans", []))

        # Также проверяем завершённые баны в actions
        actions = data.get("actions", [])
        for action_group in actions:
            for action in action_group:
                if action.get("type") == "ban" and action.get("completed"):
                    champ_id = action.get("championId")
                    if champ_id:
                        banned.add(champ_id)

        return banned

    def perform_action(self, action_id, champion_id, complete=True):
        """Выполняет действие (бан или пик) с указанным чемпионом."""
        url = f"https://127.0.0.1:{self.port}/lol-champ-select/v1/session/actions/{action_id}"
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"

        payload = {
            "championId": champion_id,
            "completed": complete
        }

        try:
            response = requests.patch(url, headers=headers, json=payload, verify=False, timeout=5)
            return response.status_code in [200, 204]
        except requests.exceptions.RequestException:
            return False


    def get_picked_champions(self):
        """Получает список уже выбранных чемпионов."""
        data = self.get_champ_select_session()
        if not data:
            return set()

        picked = set()

        # Чемпионы из моей команды
        my_team = data.get("myTeam", [])
        for player in my_team:
            champ_id = player.get("championId")
            if champ_id and champ_id != 0:
                picked.add(champ_id)

        # Чемпионы из вражеской команды
        their_team = data.get("theirTeam", [])
        for player in their_team:
            champ_id = player.get("championId")
            if champ_id and champ_id != 0:
                picked.add(champ_id)

        return picked


