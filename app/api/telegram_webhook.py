import hmac
import hashlib

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from sqlalchemy import select

from app.config import get_settings
from app.db import get_session
from app.models import Asset, Client, Submission
from app.services import pipeline, telegram_client

router = APIRouter()


def _verify_secret(secret_header: str | None) -> None:
    secret = get_settings().telegram_webhook_secret
    if secret and (not secret_header or not hmac.compare_digest(secret_header, secret)):
        raise HTTPException(status_code=403, detail="ongeldige webhook")


async def _get_or_create_client(session, telegram_user_id: int, name: str) -> Client:
    client = session.scalar(select(Client).where(Client.telegram_user_id == str(telegram_user_id)))
    if client is None:
        client = Client(telegram_user_id=str(telegram_user_id), name=name)
        session.add(client)
        session.commit()
    return client


@router.post("/api/telegram/hook")
async def telegram_hook(
    request: Request,
    background: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    session = next(get_session())
    _verify_secret(x_telegram_bot_api_secret_token)

    payload = await request.json()
    message = payload.get("message") or payload.get("edited_message") or {}
    chat_id = message.get("chat", {}).get("id")
    if not chat_id:
        return {"ok": True}

    from_user = message.get("from", {})
    client = await _get_or_create_client(session, chat_id, from_user.get("first_name", ""))

    if message.get("text", "").strip().startswith("/start"):
        link = pipeline.create_magic_link(session, client.id)
        await telegram_client.send_message(
            chat_id,
            f"Hoi {client.name or ''}! 👋\n\nStuur hier foto's, spraakberichten of tekst voor je website-update.\n\n"
            f"Of open je eigen bewerkpagina:\n{link}",
        )
        return {"ok": True}

    submission = Submission(client_id=client.id, source="telegram", status="received")
    session.add(submission)
    session.flush()

    if message.get("text"):
        from app.models import ContentVersion

        session.add(
            ContentVersion(
                submission_id=submission.id, title="", text=message["text"], is_current=True
            )
        )

    if message.get("photo"):
        file_id = message["photo"][-1]["file_id"]
        data = await telegram_client.download_file(file_id)
        rel = pipeline.store_media(submission.id, "photo", "foto.jpg", data)
        session.add(Asset(submission_id=submission.id, kind="photo", original_path=rel))

    if message.get("voice") or message.get("audio"):
        file_id = (message.get("voice") or message.get("audio"))["file_id"]
        data = await telegram_client.download_file(file_id)
        rel = pipeline.store_media(submission.id, "audio", "audio.ogg", data)
        session.add(Asset(submission_id=submission.id, kind="audio", original_path=rel))

    session.commit()
    submission_id = submission.id
    session.close()

    background.add_task(_run_pipeline, submission_id)
    return {"ok": True}


async def _run_pipeline(submission_id: int) -> None:
    from app.db import init_engine
    from app.db import get_session

    init_engine()
    gen = get_session()
    session = next(gen)
    try:
        await pipeline.process_submission(session, submission_id)
    finally:
        session.close()
