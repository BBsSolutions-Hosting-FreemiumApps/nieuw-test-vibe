import os
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.config import get_settings
from app.db import get_session
from app.models import Asset, Client, ContentVersion, MagicToken, Submission, hash_token
from app.services import pipeline

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _is_expired(expires_at) -> bool:
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)
    return expires_at < now


def _client_for_token(session, raw_token: str) -> Client:
    token = session.scalar(
        select(MagicToken).where(MagicToken.token_hash == hash_token(raw_token))
    )
    if token is None or token.revoked or _is_expired(token.expires_at):
        raise HTTPException(status_code=403, detail="link verlopen of ongeldig")
    return token.client


def _latest_content(session, submission_id: int) -> ContentVersion | None:
    return session.scalar(
        select(ContentVersion)
        .where(ContentVersion.submission_id == submission_id, ContentVersion.is_current)
        .order_by(ContentVersion.id.desc())
    )


@router.get("/bewerk/{token}", response_class=HTMLResponse)
def edit_page(request: Request, token: str):
    gen = get_session()
    session = next(gen)
    try:
        client = _client_for_token(session, token)
        submissions = session.scalars(
            select(Submission)
            .where(Submission.client_id == client.id)
            .order_by(Submission.id.desc())
            .limit(10)
        ).all()

        items = []
        for s in submissions:
            content = _latest_content(session, s.id)
            photo = session.scalar(select(Asset).where(Asset.submission_id == s.id, Asset.kind == "photo"))
            items.append(
                {
                    "id": s.id,
                    "status": s.status,
                    "title": content.title if content else "",
                    "text": content.text if content else "",
                    "photo": (photo.processed_path or photo.original_path) if photo else None,
                }
            )

        return templates.TemplateResponse(
            request,
            "edit_page.html",
            {"client_name": client.name, "token": token, "items": items},
        )
    finally:
        session.close()


@router.post("/bewerk/{token}/opslaan")
def save_content(
    token: str,
    submission_id: int = Form(...),
    title: str = Form(""),
    text: str = Form(""),
    photo: UploadFile | None = File(default=None),
    background: BackgroundTasks = None,  # type: ignore[assignment]
):
    gen = get_session()
    session = next(gen)
    try:
        client = _client_for_token(session, token)
        submission = session.scalar(
            select(Submission).where(
                Submission.id == submission_id, Submission.client_id == client.id
            )
        )
        if submission is None:
            raise HTTPException(status_code=404, detail="niet gevonden")

        latest = _latest_content(session, submission.id)
        if latest:
            latest.is_current = False
        session.add(
            ContentVersion(
                submission_id=submission.id,
                title=title.strip()[:300],
                text=text.strip(),
                is_current=True,
            )
        )

        if photo is not None and photo.filename:
            data = photo.file.read()
            rel = pipeline.store_media(submission.id, "photo", photo.filename, data)
            session.add(Asset(submission_id=submission.id, kind="photo", original_path=rel))

        submission.status = "processing"
        session.commit()
        submission_id_out = submission.id
    finally:
        session.close()

    background.add_task(_run_pipeline_sync, submission_id_out)
    return HTMLResponse(
        content=f'<script>window.location="/bewerk/{token}";</script>'
        '<p style="font-family:sans-serif;padding:2rem">✅ Opgeslagen, wordt verwerkt…</p>'
    )


def _run_pipeline_sync(submission_id: int) -> None:
    import asyncio

    gen = get_session()
    session = next(gen)
    try:
        asyncio.run(pipeline.process_submission(session, submission_id))
    finally:
        session.close()
