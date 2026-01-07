import eel

from backend.models import Champions


class Eel:
    def __init__(self):
        pass

    @staticmethod
    def log(message: str, log_type: str = "info"):
        """Send log message to UI"""
        try:
            eel.addLog(message, log_type)
        except Exception:
            print(f"[{log_type.upper()}] {message}")

    @staticmethod
    def update_connection(connected: bool, text: str):
        """Update connection status in UI"""
        try:
            eel.updateConnectionStatus(connected, text)
        except Exception:
            pass

    @staticmethod
    def update_phase(phase: str):
        """Update current phase in UI"""
        try:
            eel.updatePhase(phase)
        except Exception:
            pass

    @staticmethod
    def update_role(role: str):
        """Update current role in UI"""
        try:
            eel.updateRole(role)
        except Exception:
            pass

    @staticmethod
    def update_champions_table(champions_for_role: Champions):
        """Send champions data to UI"""
        if champions_for_role is None:
            return

        try:
            data = {
                'top': [{'name': c.name, 'id': c.id} for c in champions_for_role.top[:10]],
                'top_ban': [{'name': c.name, 'id': c.id} for c in champions_for_role.top_ban[:10]],
                'jungle': [{'name': c.name, 'id': c.id} for c in champions_for_role.jungle[:10]],
                'jungle_ban': [{'name': c.name, 'id': c.id} for c in champions_for_role.jungle_ban[:10]],
                'middle': [{'name': c.name, 'id': c.id} for c in champions_for_role.middle[:10]],
                'middle_ban': [{'name': c.name, 'id': c.id} for c in champions_for_role.middle_ban[:10]],
                'bottom': [{'name': c.name, 'id': c.id} for c in champions_for_role.bottom[:10]],
                'bottom_ban': [{'name': c.name, 'id': c.id} for c in champions_for_role.bottom_ban[:10]],
                'utility': [{'name': c.name, 'id': c.id} for c in champions_for_role.utility[:10]],
                'utility_ban': [{'name': c.name, 'id': c.id} for c in champions_for_role.utility_ban[:10]],
            }
            eel.updateChampionsTable(data)
        except Exception:
            pass

    @staticmethod
    def update_lobby(lobby: list[dict]):
        """Send lobby members to UI"""
        try:
            eel.updateLobby(lobby)
        except Exception:
            pass

    @staticmethod
    def set_buttons_state(state: bool):
        """Send button state to UI"""
        try:
            eel.setButtonsState(state)
        except Exception:
            pass

    @staticmethod
    def update_lobby_full(lobby: list[dict], phase: str | None, queue_name: str | None):
        """Send lobby full to UI"""
        try:
            eel.updateLobbyFull({
                'members': lobby,
                'phase': phase,
                'queueName': queue_name
            })
        except Exception:
            pass