from pydantic import BaseModel


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