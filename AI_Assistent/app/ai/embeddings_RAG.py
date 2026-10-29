import math
from google import genai
from google.genai import types
from AI_Assistent.config.loadenv import API_KEY
from google.genai.errors import APIError
import httpx
import time

RETRYABLE_CODES = {408, 429, 500, 502, 503, 504}

client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=1
        )
    )
    )

def cosine_similarity(a, b):
    góra = sum(x * y for x, y in zip(a, b))

    kwadrat_z_a = math.sqrt(sum(x * x for x in a))
    kwadrat_z_b = math.sqrt(sum(x * x for x in b))
    dół = kwadrat_z_a * kwadrat_z_b
    return góra / dół

documents = [
    """
Anulowanie zamówienia:
Klient może anulować zamówienie, dopóki nie zostało ono przekazane
do wysyłki. Aby anulować zamówienie, należy skontaktować się z obsługą
klienta i podać numer zamówienia.
    """,
    """
Status przesyłki:
Klient może sprawdzić status przesyłki za pomocą numeru śledzenia.
Numer jest wysyłany w wiadomości e-mail po nadaniu paczki.
Jeśli przesyłka nie dotarła w przewidywanym terminie, należy
skontaktować się z obsługą klienta.
    """,
    """
Zwroty produktów:
Klient może zwrócić zakupiony produkt w ciągu 30 dni od otrzymania
przesyłki. Produkt powinien być odpowiednio zabezpieczony na czas
transportu. Aby rozpocząć zwrot, należy wypełnić formularz zwrotu
dostępny na stronie sklepu.
    """
]

documents_parts = [
    types.Content(
        parts=[
            types.Part.from_text(text=f'''title: {d.splitlines()[1]}
text: {d}''')
        ]
    ) for d in documents
]
emb_docs = None
for i in range(3):
    try:
        embed_docs = client.models.embed_content(
            model='gemini-embedding-2',
            contents=documents_parts
        )
        emb_docs = [(documents[i], emb.values) for i, emb in enumerate(embed_docs.embeddings)]
        break
    except APIError as e:
        if i == 2:
            break
        elif e.code in RETRYABLE_CODES:
            time.sleep(i + 1)
            continue
        else:
            break

    except (httpx.TimeoutException, httpx.NetworkError):
        if i == 2:
            break
        else:
            time.sleep(i + 1)
            continue


def rag_search(query: str) -> dict:
    """
    This tool searches through the documentation. Should be used when message is about company's internal proceses like order state or delivery's state.
    In any error case response will return success = False, no documents and error's details.
    If everything goes well then response will return success + True, found documents and no errors.
    """
    if emb_docs is None:
        return {
            'success': False,
            'documents': [],
            'error': {
                'type': 'Documents_unavailable',
                'message': 'No connection to the database.'
            }
        }
    result = None
    for i in range(3):
        try:
            result = client.models.embed_content(
                model='gemini-embedding-2',
                contents=f'''task: question answering |
                query: {query}'''
            )
            break
        except APIError as e:
            if i == 2:
                break
            elif e.code in RETRYABLE_CODES:
                time.sleep(i + 1)
                continue
            else:
                break
        
        except (httpx.TimeoutException, httpx.NetworkError):
            if i == 2:
                break
            else:
                time.sleep(i + 1)
                continue


    if result is None:
        return {
            'success': False,
            'documents': [],
            'error': {
                'type': 'Embedding query error',
                'message': 'Error with generating embedding vector for asked query.'
            }
        }

    accuracy = []
    for emb in emb_docs:
        similarity = cosine_similarity(result.embeddings[0].values, emb[1])
        accuracy.append((emb[0], similarity))
    accuracy.sort(key=lambda x: x[1], reverse=True)
    bests = []
    for i in accuracy[:2]:
        bests.append(i[0])
    return {
        'success': True,
        'documents': bests,
        'error': None
    }