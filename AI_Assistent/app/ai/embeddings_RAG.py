import math
from google import genai
from google.genai import types
from AI_Assistent.config.loadenv import API_KEY

client = genai.Client(api_key=API_KEY)

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

embed_docs = client.models.embed_content(
    model='gemini-embedding-2',
    contents=documents_parts
)
emb_docs = [(documents[i], emb.values) for i, emb in enumerate(embed_docs.embeddings)]

def rag_search(query: str) -> list:
    result = client.models.embed_content(
        model='gemini-embedding-2',
        contents=f'''task: question answering |
        query: {query}'''
    )

    accuracy = []
    for emb in emb_docs:
        similarity = cosine_similarity(result.embeddings[0].values, emb[1])
        accuracy.append((emb[0], similarity))
    accuracy.sort(key=lambda x: x[1], reverse=True)
    bests = []
    for i in accuracy[:2]:
        bests.append(i[0])
    return bests