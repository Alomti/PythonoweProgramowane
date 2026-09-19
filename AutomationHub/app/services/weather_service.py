import httpx
from datetime import datetime
from AutomationHub.app.models.save_json_model import read_json, replace_content

async def get_weather(key, city, timeout, path):
    cache = read_json(path, 'dir')
    now = datetime.now()
    if city in cache:
        diffrience = now - cache[city]['request_time']
        if diffrience.total_seconds() < 60:
            return cache[city]['weather']
    url = 'https://api.weatherapi.com/v1/current.json'
    params = {'key': key, 'q': city}
    async with httpx.AsyncClient() as client:
        response = await client.get(url , params=params, timeout=timeout)
        now = datetime.now()
        response.raise_for_status()
        raw = response.json()
    weather = {
        'temp': raw['current']['temp_c'],
        'wind_Speed': raw['current']['wind_kph'],
        'chance_of_rain': raw['current']['will_it_rain']
        }
    cache[city] = {
            'weather': weather,
            'request_time': now     
        }
    replace_content(path, cache)
    return weather