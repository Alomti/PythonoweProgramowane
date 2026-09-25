import os
from dotenv import load_dotenv
import httpx
import json
load_dotenv()
API_key = os.getenv('AI_KEY')

def AI_response(key, model_name, content):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    headers = {
        'x-goog-api-key': key,
        'Content-Type': 'application/json'
    }
    body = {
        'systemInstruction': {
            'parts': [
                {
                    'text': 'You are service asistent and your task is to deduce what client want and fulfill "intent", "product" and "reason"'
                }
            ]
        },
        'contents': [
            {
                'parts': [
                    {
                        'text': content
                    }
                ]
            }
        ],
        'generationConfig': {
            'responseMimeType': 'application/json',
            'responseSchema': {
                'type': 'object',
                'properties': {
                    'intent': {
                        'type': 'string',
                        'enum': [
                            'return',
                            'cancel_order',
                            'order_state'
                        ]
                    },
                    'product': {
                        'type': 'string'
                    },
                    'reason': {
                        'type': 'string',
                        'nullable': True
                    }
                },
                'required': [
                    'intent',
                    'product',
                    'reason'
                ]
            }
        }
    }
    response = httpx.post(url=url, headers=headers, json=body, timeout=30)
    response.raise_for_status()
    data = response.json()
    return json.dumps(data['candidates'][0]['content']['parts'][0]['text'], indent=4)
print(AI_response(API_key, 'gemini-3.6-flash', 'Chciałbym zwrócić książkę pod tytułem "Niziołek to znaczy tam i tu" ponieważ zabijają tam smoka'))