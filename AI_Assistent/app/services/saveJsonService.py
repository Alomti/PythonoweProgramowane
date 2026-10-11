import json
from pathlib import Path
from google.genai import types
def read_json(file: Path):
    if not file.exists():
        file.touch()
    if file.stat().st_size == 0:
        with open(file, 'w', encoding='utf-8'):
            json.dump([])
    with open(file, 'r', encoding='utf-8') as f:
        content = json.load(f)
        return content

def save_json(file, content):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)

def load_history_from_json(file):
    if not Path(file).exists():
        return []
    history = read_json(file)
    if history == []:
        return history
    deserialized = []
    for i in history:
        parts = []
        if i.get('text'):
            parts.append(
                types.Part.from_text(
                    text=i['text']
                )
            )
        if i.get('file_data'):
            parts.append(
                types.Part.from_text(
                    text=f'Użyto pliku {i["file_data"]["file_name"]} ({i["file_data"]["file_type"]})'
                )
            )
        content = types.Content(
            role=i['role'],
            parts=parts
        )
        deserialized.append(content)
    return deserialized