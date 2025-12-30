from pathlib import Path


def load_or_create_config(file_path: Path, base_file_path: Path):
    if file_path.exists() and file_path.is_file():
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return text
    else:
        with open(base_file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return text