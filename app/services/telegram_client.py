import httpx

from app.config import get_settings

API_BASE = "https://api.telegram.org"


def _token() -> str:
    return get_settings().telegram_bot_token


async def download_file(file_id: str) -> bytes:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(f"{API_BASE}/bot{_token()}/getFile", params={"file_id": file_id})
        resp.raise_for_status()
        file_path = resp.json()["result"]["file_path"]
        dl = await client.get(f"{API_BASE}/file/bot{_token()}/{file_path}", timeout=120)
        dl.raise_for_status()
        return dl.content


async def send_message(chat_id: int | str, text: str) -> None:
    if not _token():
        return
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(f"{API_BASE}/bot{_token()}/sendMessage", json={"chat_id": chat_id, "text": text})
