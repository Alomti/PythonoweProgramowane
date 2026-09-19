from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
from json import JSONDecodeError
import asyncio
import logging
logger = logging.getLogger(__name__)
try:
    from AutomationHub.app.config.load_env import weather_KEY, timeout, data_file_path, cache_path
except ValueError as e:
    logger.error(f'Error with geting API keys. {e}')
    raise SystemExit(1)
from AutomationHub.app.services.weather_service import get_weather
from AutomationHub.app.models.weather_model import WeatherModel, HistoryModel, AddWeather, AddResponse
from AutomationHub.app.models.save_json_model import read_json, add_to_json
from AutomationHub.app.services.cleanup_service import cleanup_cache
hand_mades = Path(__file__).parent / data_file_path
cache = Path(__file__).parent / cache_path
if not hand_mades.exists():
    hand_mades.touch()
if not cache.exists():
    cache.touch()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print('Backend starting...')
        cln_cache = asyncio.create_task(cleanup_cache(cache))

        yield

        cln_cache.cancel()
    except FileNotFoundError as e:
        logger.error(f'Unexpected error with json file: {e}')
        raise HTTPException(
            status_code=500,
            detail='Unexpected error with json file'
        )


app = FastAPI(lifespan=lifespan)



@app.get('/weather', response_model=WeatherModel)
async def put_out_weather(city: str) -> WeatherModel:
    try:
        result = await get_weather(weather_KEY, city, timeout, cache)
        model = WeatherModel(**result)

    except httpx.TimeoutException:
        logger.error('Timeout with WeatherApi connection')
        raise HTTPException(
            status_code=504,
            detail='To long waiting time for response from weather API'
        )
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        if status_code == 500:
            logger.error(f'HTTPError code: {status_code}')
            raise HTTPException(
                status_code=503,
                detail='Weather API have internal problem beyond our influence'
            )
        elif status_code == 400:
            logger.error(f'HTTPError code: {status_code}')
            raise HTTPException(
                status_code=400,
                detail='Bad Request'
            )
        elif status_code in (401, 403):
            logger.error(f'HTTPError code: {status_code}')
            raise HTTPException(
                status_code=502,
                detail='Bad Gateway'
            )
        elif status_code == 404:
            logger.error(f'HTTPError code: {status_code}')
            raise HTTPException(
                status_code=404,
                detail='Not Found That City'
            )
        elif status_code in (429, 502, 503):
            logger.error(f'HTTPError code: {status_code}')
            raise HTTPException(
                status_code=503,
                detail='Service Unavailable'
            )
        else:
            logger.error(f'Unexcepted error {e}')
            raise HTTPException(
                status_code=500,
                detail='Unexcepted requuests error'
            )
            
    except httpx.ConnectError as e:
        logger.error(f'Cnonection Error {e} with Weather API')
        raise HTTPException(
            status_code=503,
            detail='Failed to connect with Weather API'
        )
    except httpx.RequestError as e:
        logger.error(f'Unexpected requests error: {e}')
        raise HTTPException(
            status_code=500,
            detail='Unexpected requests error'
        )
    except FileNotFoundError as e:
        logger.error(f'Unexpected error with json file: {e}')
        raise HTTPException(
            status_code=500,
            detail='Unexpected error with json file'
        )
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        raise HTTPException(
            status_code=500,
            detail='Unexpected error'
        )
    return model

@app.post('/weather/addWeather', response_model=AddResponse, status_code=201)
async def put_out_weather(data: AddWeather) -> AddResponse:
    try:
        add_to_json(hand_mades, data)
        message = 'Thanks for updating weather in your location'
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        raise HTTPException(
            status_code=500,
            detail='Unexpected error'
        )
    return AddResponse(message)

@app.get('/weather/handMadeHistory', response_model=HistoryModel)
def get_id() -> HistoryModel:
    try:
        history = read_json(hand_mades, 'list')
    except JSONDecodeError as e:
        logger.error(f'Unexpected error with opening json: {e}')
        raise HTTPException(
            status_code=500,
            detail='Unexpected error'
        )
    except FileNotFoundError as e:
        logger.error(f'Unexpected error with json file: {e}')
        raise HTTPException(
            status_code=500,
            detail='Unexpected error with json file'
        )
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        raise HTTPException(
            status_code=500,
            detail='Unexpected error'
        )
    return HistoryModel(history)