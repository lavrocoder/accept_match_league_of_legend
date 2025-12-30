import requests


class RiotDdragonAPI:
    def __init__(self):
        self.version = None

    def get_version(self) -> str:
        if self.version is None:
            last_version = self.get_versions()[0]
            self.version = last_version
        return self.version

    @staticmethod
    def get_versions() -> list[str]:
        url = "https://ddragon.leagueoflegends.com/api/versions.json"
        versions = requests.get(url).json()
        return versions

    def get_champions(self, version: str = None, language_code: str = "ru_RU") -> dict:
        if version is None:
            version = self.get_version()
        url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/{language_code}/champion.json"
        champions = requests.get(url).json()
        return champions