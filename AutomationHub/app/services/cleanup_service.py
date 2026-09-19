from datetime import datetime
import asyncio
from AutomationHub.app.models.save_json_model import read_json, replace_content

async def cleanup_cache(path):
    while True:
        await asyncio.sleep(180)
        cache = read_json(path, 'dir')
        now = datetime.now()
        keys_to_delate = []
        for key, value in cache.items():
            diffrence = now - value['request_time']
            if diffrence.total_seconds() > 60:
                keys_to_delate.append(key)
        for key in keys_to_delate:
            del cache[key]
        replace_content(path, cache)