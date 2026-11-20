import logging
import math
import re
import json
from collections import Counter

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AIProviderError(RuntimeError):
    pass


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def relevant_context(question: str, documents: list[str], limit: int = 4) -> str:
    """Dependency-free hybrid lexical retrieval with normalized term scoring."""
    terms = set(re.findall(r"\w{3,}", question.lower()))
    if not terms:
        return ""
    ranked: list[tuple[int, str]] = []
    for document in documents:
        chunks = [part.strip() for part in re.split(r"(?<=[.!?\n])\s+", document) if part.strip()]
        for chunk in chunks:
            chunk_terms = Counter(re.findall(r"\w{3,}", chunk.lower()))
            overlap = sum(chunk_terms[term] for term in terms)
            question_phrases = set(re.findall(r"\w+", question.lower()))
            chunk_phrases = set(re.findall(r"\w+", chunk.lower()))
            phrase_score = len(question_phrases & chunk_phrases)
            score = overlap * 3 + phrase_score
            if score:
                ranked.append((score, chunk))
    ranked.sort(key=lambda entry: entry[0], reverse=True)
    return "\n".join(text for _, text in ranked[:limit])[:6000]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


_embedding_cache: dict[str, list[float]] = {}


async def embed_text(text: str) -> list[float]:
    cache_key = text[:8000]
    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]
    if not cache_key:
        return []
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.openai_base_url.rstrip('/')}/embeddings",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": settings.openai_embedding_model, "input": text[:8000]},
        )
        response.raise_for_status()
        vector = response.json()["data"][0]["embedding"]
        embedding = [float(value) for value in vector]
        if len(_embedding_cache) >= 256:
            _embedding_cache.pop(next(iter(_embedding_cache)))
        _embedding_cache[cache_key] = embedding
        return embedding


async def hybrid_context(question: str, documents: list[str], limit: int = 4) -> str:
    lexical = relevant_context(question, documents, limit=limit)
    lexical_chunks = [chunk for chunk in lexical.split("\n") if chunk]
    if not settings.openai_api_key:
        return lexical
    try:
        question_embedding = await embed_text(question)
        if not question_embedding:
            return lexical
        ranked: list[tuple[float, str]] = []
        for document in documents:
            chunks = [part.strip() for part in re.split(r"(?<=[.!?\n])\s+", document) if part.strip()]
            for chunk in chunks[:20]:
                chunk_embedding = await embed_text(chunk)
                score = cosine_similarity(question_embedding, chunk_embedding)
                if score > 0.72:
                    ranked.append((score, chunk))
        ranked.sort(key=lambda entry: entry[0], reverse=True)
        selected = []
        for _, chunk in ranked:
            if chunk not in selected:
                selected.append(chunk)
            if len(selected) >= limit:
                break
        for chunk in lexical_chunks:
            if chunk not in selected:
                selected.append(chunk)
            if len(selected) >= limit:
                break
        return "\n".join(selected)[:6000]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        logger.exception("Falha ao calcular embeddings; usando busca lexical")
        return lexical


async def hybrid_chunk_context(
    question: str,
    chunks: list[tuple[str, list[float] | None]],
    limit: int = 4,
) -> str:
    lexical = relevant_context(
        question,
        [content for content, _ in chunks],
        limit=limit,
    )
    if not settings.openai_api_key:
        return lexical
    try:
        question_embedding = await embed_text(question)
        ranked: list[tuple[float, str]] = []
        for content, embedding in chunks:
            if embedding:
                score = cosine_similarity(question_embedding, embedding)
                if score > 0.72:
                    ranked.append((score, content))
        ranked.sort(key=lambda entry: entry[0], reverse=True)
        selected = [
            content
            for _, content in ranked[:limit]
        ]
        for content in lexical.split("\n"):
            if content and content not in selected:
                selected.append(content)
            if len(selected) >= limit:
                break
        return "\n".join(selected)[:6000]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        logger.exception("Falha ao recuperar embeddings persistidos; usando busca lexical")
        return lexical


async def generate_answer(
    instructions: str,
    question: str,
    context: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    if settings.openai_api_key:
        messages = [{"role": "system", "content": instructions}]
        if context:
            messages.append({"role": "system", "content": f"Informações da empresa (use somente quando relevantes):\n{context}"})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": settings.openai_model,
                        "messages": messages,
                        "temperature": 0.4,
                        "max_tokens": settings.ai_max_output_tokens,
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("The provider returned an empty or invalid response")
                return content.strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            logger.exception("Falha ao gerar resposta com o provedor de IA configurado")
            raise AIProviderError(
                "O serviço de IA está indisponível no momento. Tente novamente."
            ) from exc
    normalized_question = re.sub(r"[^\w]", "", question.lower())
    greeting_words = {"oi", "ola", "olae", "bomdia", "boatarde", "boanoite"}
    if normalized_question in greeting_words:
        return "Olá! Como posso ajudar? Posso responder sobre produtos, horários e políticas do estabelecimento."
    if context:
        return f"Encontrei estas informações que podem ajudar:\n\n{context}\n\nSe precisar, conte um pouco mais sobre sua dúvida."
    return "Ainda não tenho informações suficientes para responder com segurança. Entre em contato com a equipe para receber ajuda."
