from app.config import CHAMPIONS_FILE
from app.utils import get_or_download_champions


def main():
    print("Загрузка героев")
    ddragon_data = get_or_download_champions(CHAMPIONS_FILE)
    for champion in ddragon_data['data'].values():
        print(champion['name'])


if __name__ == '__main__':
    main()