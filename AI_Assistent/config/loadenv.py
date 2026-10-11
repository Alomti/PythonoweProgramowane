import os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv('AI_KEY')
if not API_KEY:
    raise ValueError('Missing "AI_KEY" in .env file.')
AI_MODEL = os.getenv('AI_MODEL')
if not AI_MODEL:
    raise ValueError('Missing "AI_MODEL" in .env file.')