from datetime import datetime
import asyncio
from AutomationHub.app.models.save_json_model import read_json, replace_content

async def cleanup_cache(path):
    while True:
        await asyncio.sleep(5)
        cache = read_json(path, 'dir')
        now = datetime.isoformat(datetime.now())
        keys_to_delete = []
        for key, value in cache.items():
            difference = datetime.fromisoformat(now) - datetime.fromisoformat(value['request_time'])
            if difference.total_seconds() > 60:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del cache[key]
        replace_content(path, cache)