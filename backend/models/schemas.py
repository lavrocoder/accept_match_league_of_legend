from pydantic import BaseModel
from rich.console import Console
from rich.table import Table


class Champion(BaseModel):
    id: int
    name: str
    alias: str
    level: int
    points: int
    by: str = 'Мастерство'


class ChampionsByRoleAndMastery(BaseModel):
    """Чемпионы сгруппированные по ролям и отсортированные по мастерству"""
    top: list[Champion] = []
    jungle: list[Champion] = []
    middle: list[Champion] = []
    bottom: list[Champion] = []
    utility: list[Champion] = []

    def sort_by_mastery(self):
        self.top.sort(key=lambda c: (c.level, c.points), reverse=True)
        self.jungle.sort(key=lambda c: (c.level, c.points), reverse=True)
        self.middle.sort(key=lambda c: (c.level, c.points), reverse=True)
        self.bottom.sort(key=lambda c: (c.level, c.points), reverse=True)
        self.utility.sort(key=lambda c: (c.level, c.points), reverse=True)



class Champions(BaseModel):
    top: list[Champion] = []
    top_ban: list[Champion] = []
    jungle: list[Champion] = []
    jungle_ban: list[Champion] = []
    middle: list[Champion] = []
    middle_ban: list[Champion] = []
    bottom: list[Champion] = []
    bottom_ban: list[Champion] = []
    utility: list[Champion] = []
    utility_ban: list[Champion] = []

    def exists(self, role: str, champion: Champion):
        for champ in getattr(self, role):
            if champ.name == champion.name:
                return True
        return False

    def print_table(self, limit: int = 10):
        table = Table(title='Чемпионы по ролям')

        role_groups = [
            ('Топ', ['top', 'top_ban']),
            ('Лес', ['jungle', 'jungle_ban']),
            ('Мид', ['middle', 'middle_ban']),
            ('Бот', ['bottom', 'bottom_ban']),
            ('Саппорт', ['utility', 'utility_ban']),
        ]

        for group_name, _ in role_groups:
            table.add_column(f'{group_name}', justify='center')
            table.add_column(f'бан', justify='center')

        columns = []
        for _, roles in role_groups:
            for role in roles:
                champs = getattr(self, role)[:limit]
                columns.append([c.name for c in champs])

        for i in range(limit):
            row = [col[i] if i < len(col) else '' for col in columns]
            table.add_row(*row)

        console = Console()
        console.print(table)

    def get_presets_for_role(self, role: str) -> tuple[list[Champion], list[Champion]]:
        return getattr(self, role), getattr(self, f"{role}_ban")