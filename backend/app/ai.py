import re
from collections import Counter

from app.config import settings


def relevant_context(question: str, documents: list[str], limit: int = 4) -> str:
    """Simple dependency-free lexical retrieval; replaceable with a vector store later."""
    terms = set(re.findall(r"\w{3,}", question.lower()))
    if not terms:
        return ""
    ranked: list[tuple[int, str]] = []
    for document in documents:
        chunks = [part.strip() for part in re.split(r"(?<=[.!?\n])\s+", document) if part.strip()]
        for chunk in chunks:
            score = sum(Counter(re.findall(r"\w{3,}", chunk.lower()))[term] for term in terms)
            if score:
                ranked.append((score, chunk))
    ranked.sort(key=lambda entry: entry[0], reverse=True)
    return "\n".join(text for _, text in ranked[:limit])[:6000]


async def generate_answer(instructions: str, question: str, context: str) -> str:
    if settings.openai_api_key:
        import httpx

        messages = [{"role": "system", "content": instructions}]
        if context:
            messages.append({"role": "system", "content": f"Informações da empresa (use somente quando relevantes):\n{context}"})
        messages.append({"role": "user", "content": question})
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={"model": settings.openai_model, "messages": messages, "temperature": 0.4},
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError):
            return "No momento não consegui acessar o assistente. Tente novamente em instantes."
    if context:
        return f"Encontrei estas informações que podem ajudar:\n\n{context}\n\nSe precisar, conte um pouco mais sobre sua dúvida."
    return "Ainda não tenho informações suficientes para responder com segurança. Entre em contato com a equipe para receber ajuda."
