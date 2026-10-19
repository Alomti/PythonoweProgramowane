import math
from google import genai
from google.genai import types
from AI_Assistent.config.loadenv import API_KEY

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
    types.Content(parts=[types.Part.from_text(text=d)]) for d in documents
]

def cosine_similarity(a, b):
    góra = sum(x * y for x, y in zip(a, b))

    kwadrat_z_a = math.sqrt(sum(x * x for x in a))
    kwadrat_z_b = math.sqrt(sum(x * x for x in b))
    dół = kwadrat_z_a * kwadrat_z_b
    return góra / dół


client = genai.Client(api_key=API_KEY)
result = client.models.embed_content(
    model='gemini-embedding-2',
    contents='I received my order but I want to cancel it. What should I do?'
)

result2 = client.models.embed_content(
    model='gemini-embedding-2',
    contents=documents_parts
)
print("Liczba dokumentów:", len(documents))
print("Liczba embeddingów:", len(result2.embeddings))
print("Typ odpowiedzi:", type(result2))

accuracy = []
for i, emb in enumerate(result2.embeddings):
    print(f'Working at {i}')
    similarity = cosine_similarity(result.embeddings[0].values, emb.values)
    accuracy.append((documents[i], similarity))
accuracy.sort(key=lambda x: x[1], reverse=True)
print(accuracy)