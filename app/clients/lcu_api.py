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

    def get_champions_for_role_by_mastery(self):
        champions = self.get_champions()
        mastery = self.get_champions_mastery()
        recommended_positions = self.get_recommended_champion_positions()

        print()

