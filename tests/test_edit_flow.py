from sqlalchemy import select

from app.db import get_session
from app.models import Client, ContentVersion, Submission, new_magic_token
from app.services import pipeline


def _make_client_with_submission(session):
    client = Client(telegram_user_id="12345", name="Test")
    session.add(client)
    session.commit()
    sub = Submission(client_id=client.id, source="web", status="klaar")
    session.add(sub)
    session.commit()
    session.add(ContentVersion(submission_id=sub.id, title="Oud", text="oude tekst", is_current=True))
    session.commit()
    return client, sub


def test_edit_page_shows_content(client):
    gen = get_session()
    session = next(gen)
    cl, _sub = _make_client_with_submission(session)
    link = pipeline.create_magic_link(session, cl.id)
    token = link.rsplit("/", 1)[-1]
    session.close()

    resp = client.get(f"/bewerk/{token}")
    assert resp.status_code == 200
    assert "oude tekst" in resp.text
    assert "Test" in resp.text


def test_edit_page_rejects_bad_token(client):
    resp = client.get("/bewerk/onzin-token")
    assert resp.status_code == 403


def test_save_creates_new_version(client):
    gen = get_session()
    session = next(gen)
    cl, sub = _make_client_with_submission(session)
    link = pipeline.create_magic_link(session, cl.id)
    token = link.rsplit("/", 1)[-1]
    session.close()

    resp = client.post(
        f"/bewerk/{token}/opslaan",
        data={"submission_id": sub.id, "title": "Nieuwe titel", "text": "nieuwe tekst"},
    )
    assert resp.status_code == 200

    session = next(get_session())
    versions = session.scalars(
        select(ContentVersion).where(ContentVersion.submission_id == sub.id)
    ).all()
    assert len(versions) == 2
    assert versions[-1].title == "Nieuwe titel"
    assert versions[-1].is_current is True
    session.close()


def test_magic_token_roundtrip():
    raw, token_hash, _expires = new_magic_token(30)
    from app.models import hash_token

    assert hash_token(raw) == token_hash
    assert len(raw) > 30
