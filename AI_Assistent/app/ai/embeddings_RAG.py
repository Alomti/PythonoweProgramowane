import sys
from pathlib import Path
pp = Path(__file__).resolve().parents[3]
if str(pp) not in sys.path:
    sys.path.insert(0,str(pp))



import math
from google import genai
from google.genai import types
from AI_Assistent.config.loadenv import API_KEY
from google.genai.errors import APIError
import httpx
import time
from pathlib import Path
import hashlib
from AI_Assistent.app.services.saveJsonService import read_json, save_json

RETRYABLE_CODES = {408, 429, 500, 502, 503, 504}

docdir = Path(__file__).parents[1] / 'data' / 'documents'

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

def generate_embeddings(text, role):
    if role == 'document':
        content = f'''title: {text['title']}
text: {text['content']}'''
    else:
        content = f'''task: Question answering |
query: {text}'''
    for i in range(3):
        try:
            result = client.models.embed_content(
                model='gemini-embedding-2',
                contents=content
            )
            return result.embeddings[0].values
        except APIError as e:
            print(e)
            if i == 2:
                return None
            elif e.code in RETRYABLE_CODES:
                time.sleep(i + 1)
                continue
            else:
                return None
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as e:
            print(e)
            if i == 2:
                return None
            else:
                time.sleep(i + 1)
                continue

def load_documents():
    documents = []
    docfiles = docdir.glob('*.md')

    for document in docfiles:
        text = document.read_text(encoding='utf-8')
        lines = text.splitlines()
        title = lines[0]
        if not title.startswith('# ') or not title[2:].strip():
            # teraz print w przyszłości log tego przypadku i w GUI jak będzie to okienko mówiące o tym użytkownikowi
            print(f'Failed with loading {document.name} due to incorrect format.')
            continue
        title = title.removeprefix('# ').strip()
        docbody = '\n'.join(lines[1:]).strip()
        documents.append({
            'title': title,
            'content': docbody,
            'source': document.name
        })
    if documents == []:
        raise ValueError('No document found in document folder')
    return documents


def load_cache():
    cache = docdir.parent / 'embeddings.json'
    cache = read_json(cache)
    return cache

def sync_embeddings():
    documents = load_documents()
    cache = load_cache()


    doc_keys = {d['source']: d for d in documents}
    cache_keys = {c['source']: c for c in cache}

    paired_keys = doc_keys.keys() & cache_keys.keys()

    paired = [{
        'source': doc_keys[k]['source'],
        'title': doc_keys[k]['title'],
        'content': doc_keys[k]['content'],
        'embedding': cache_keys[k]['embedding'],
        'hash': cache_keys[k]['hash']
    } for k in paired_keys]
    unpaired_docs = [doc_keys[k] for k in doc_keys.keys() - cache_keys.keys()]

    for p in paired:
        hash_text = hashlib.sha256(p['content'].encode("utf-8")).hexdigest()
        if hash_text != p['hash']:
            new_emb = generate_embeddings(p, 'document')
            if new_emb is None:
                paired.remove(p)
                # teraz print w przyszłości log tego przypadku i w GUI jak będzie to okienko mówiące o tym użytkownikowi
                print(f'Error with creating embedding for document: {p['source']} This document will be ignored during operations requiring documents.')
                continue
            p['hash'] = hash_text
            p['embedding'] = new_emb
            print(f'Nowy embedding dla zmienionego dokumentu {p['title']}')

    for d in unpaired_docs:
        d['hash'] = hashlib.sha256(d['content'].encode("utf-8")).hexdigest()
        new_emb = generate_embeddings(d, 'document')
        if new_emb is None:
            # teraz print w przyszłości log tego przypadku i w GUI jak będzie to okienko mówiące o tym użytkownikowi
            print(f'Error with creating embedding for document: {d['source']} This document will be ignored during operations requiring documents.')
            continue
        d['embedding'] = new_emb
        paired.append(d)
        print(f'Nowy embedding dla nowego dokumentu {d['title']}')

    save_json(docdir.parent / 'embeddings.json', paired)
    return paired

def rag_search(query: str) -> dict:
    """
    Searches the documentation using semantic similarity.

    Use this tool for questions about company-specific processes,
    such as order cancellation, returns, and delivery status.

    Returns the two most similar documents when the search succeeds.
    Returns success=False and error details if the search fails.
    """
    documents = sync_embeddings()
    result = generate_embeddings(query, 'query')

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
    for d in documents:
        full_text = d['title'] + '\n' + d['content']
        similarity = cosine_similarity(result, d['embedding'])
        accuracy.append((full_text, similarity))
    accuracy.sort(key=lambda x: x[1], reverse=True)
    bests = []
    for i in accuracy[:2]:
        bests.append(i[0])
    return {
        'success': True,
        'documents': bests,
        'error': None
    }
print(rag_search('Jak zwrócić niechciany produkt?'))