import json
from pathlib import Path
def read_json(file: Path, data_type):
    if not file.exists():
        raise FileNotFoundError
    if file.stat().st_size == 0:
        if data_type == 'dir':
            with open(file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        else:
            with open(file, 'w', encoding='utf-8') as f:
                json.dump([], f)
    with open(file, 'r', encoding='utf-8') as f:
        content = json.load(f)
        return content

def add_to_json(file: Path, newcontent, data_type):
    if file.stat().st_size == 0:
        with open(file, 'w', encoding='utf-8') as f:
            json.dump([], f)
    content = read_json(file, data_type)
    content.append(newcontent)
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)

def replace_content(file, newcontent):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(newcontent, f, indent=4, ensure_ascii=False)