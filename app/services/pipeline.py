import os

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Asset, ContentVersion, Submission, new_magic_token
from app.services import image_optimize, rewrite, telegram_client, transcribe
from app.services.storage import save_upload


async def process_submission(session: Session, submission_id: int) -> None:
    """Volledige verwerkingspipeline voor één submission:
    audio -> Whisper -> herschrijving, foto's -> optimalisatie."""
    submission = session.get(Submission, submission_id)
    if submission is None:
        return
    submission.status = "processing"
    session.commit()

    try:
        raw_text_parts: list[str] = []
        for asset in submission.assets:
            if asset.kind == "audio":
                with open(os.path.join(get_settings().media_dir, asset.original_path), "rb") as f:
                    audio_bytes = f.read()
                asset.transcript = await transcribe.transcribe(audio_bytes)
                if asset.transcript:
                    raw_text_parts.append(asset.transcript)
            elif asset.kind == "photo":
                asset.processed_path = image_optimize.optimize_image(
                    asset.original_path, get_settings().media_dir
                )
            session.commit()

        if raw_text_parts:
            text_to_process = "\n".join([p for p in raw_text_parts if p])
            rewritten = await rewrite.rewrite(text_to_process)
            title, _, body = rewritten.partition("\n")
            latest = (
                session.query(ContentVersion)
                .filter_by(submission_id=submission.id, is_current=True)
                .order_by(ContentVersion.id.desc())
                .first()
            )
            if latest:
                latest.is_current = False
            session.add(
                ContentVersion(
                    submission_id=submission.id,
                    title=title.strip()[:300],
                    text=body.strip(),
                    is_current=True,
                )
            )
            session.commit()

        submission.status = "klaar"
        session.commit()
        await telegram_client.send_message(
            submission.client.telegram_user_id or "",
            "✅ Je update is verwerkt. Tik hier om te bekijken/wijzigen.",
        )
    except Exception as exc:  # noqa: BLE001
        submission.status = "error"
        submission.error = str(exc)[:1000]
        session.commit()


def store_media(submission_id: int, kind: str, filename: str, data: bytes) -> str:
    settings = get_settings()
    rel = save_upload(settings.media_dir, f"{kind}/{submission_id}", filename, data)
    return rel


def create_magic_link(session: Session, client_id: int) -> str:
    settings = get_settings()
    raw, token_hash, expires = new_magic_token(settings.magic_link_ttl_days)
    from app.models import MagicToken

    session.add(MagicToken(client_id=client_id, token_hash=token_hash, expires_at=expires))
    session.commit()
    return f"{settings.base_url}/bewerk/{raw}"
