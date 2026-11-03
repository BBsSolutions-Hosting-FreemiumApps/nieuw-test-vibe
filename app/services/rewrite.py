import httpx

from app.config import get_settings

CHAT_URL = "https://api.openai.com/v1/chat/completions"

SYSTEM_PROMPT = (
    "Je bent een Nederlandse SEO-copywriter. Herschrijf de tekst van een lokale klant "
    "naar heldere, vindbare webtekst (Nederlands). Geef ALLEEN de herschreven tekst terug, "
    "zonder uitleg. Behoud de feitelijke informatie. Maximaal 250 woorden. "
    "Geef optioneel eerst een korte pakkende titel op de eerste regel."
)


async def rewrite(text: str) -> str:
    """SEO-herschrijving via OpenAI (GPT). Zonder API-key: originele tekst terug."""
    api_key = get_settings().openai_api_key
    if not api_key or not text.strip():
        return text
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            CHAT_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": get_settings().ai_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
