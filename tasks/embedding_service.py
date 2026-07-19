import math
import anthropic
from django.conf import settings

# Anthropic doesn't currently expose a first-party embeddings endpoint, so we use
# Voyage AI's embedding models — Anthropic's recommended embeddings partner.
# (If VOYAGE_API_KEY isn't set, embedding calls raise clearly rather than failing silently.)
import voyageai

EMBEDDING_MODEL = "voyage-3-lite"


def get_voyage_client():
    return voyageai.Client(api_key=settings.VOYAGE_API_KEY)


def embed_text(text):
    client = get_voyage_client()
    result = client.embed([text], model=EMBEDDING_MODEL, input_type="document")
    return result.embeddings[0]


def embed_query(text):
    client = get_voyage_client()
    result = client.embed([text], model=EMBEDDING_MODEL, input_type="query")
    return result.embeddings[0]


def cosine_similarity(vec_a, vec_b):
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
