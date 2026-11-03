# Content Motor 🚀

Content Ingestion & AI-Automatisering: klanten sturen updates (foto, spraak, tekst) via een **Telegram-bot** of een **magic-link bewerkpagina** op mobiel/tablet. De motor verwerkt alles automatisch: spraak → tekst (Whisper), SEO-herschrijving (GPT) en foto-optimalisatie.

## Flow

```
Telegram-bericht of bewerkpagina
   └─► FastAPI-motor
         ├─ audio → OpenAI Whisper → tekst
         ├─ tekst → SEO-herschrijving (GPT)
         ├─ foto  → resize + WebP (Pillow)
         └─ PostgreSQL (versies + herstel) + lokale media-opslag
```

## Snel starten (lokaal)

```bash
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
# → http://localhost:8000/healthz
pytest
```

## Deploy op Render (aanbevolen, geen eigen server nodig)

1. Push deze repo naar GitHub.
2. Ga naar [render.com](https://render.com) → **New → Blueprint** → kies deze repo.
   De `render.yaml` regelt app + PostgreSQL + disk automatisch.
3. Vul de secrets in: `BASE_URL`, `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`.
4. Na deploy: registreer de Telegram-webhook (eenmalig):

```bash
curl "https://api.telegram.org/bot<JOUW_TOKEN>/setWebhook?url=https://jouw-app.onrender.com/api/telegram/hook?secret=<JOUW_SECRET>"
```

> **Tip:** zonder `TELEGRAM_BOT_TOKEN` of `OPENAI_API_KEY` draait de app ook — transcriptie/herschrijving worden dan overgeslagen. Zo kun je gratis testen.

## Alternatief: eigen Coolify-VPS

```bash
docker compose up -d
```

Zelfde image; zet `DATABASE_URL` naar de PostgreSQL-container en koppel je domein met TLS in Coolify.

## Klantgebruik

- Klant start de Telegram-bot → krijgt **magic link** (30 dagen geldig, geen wachtwoord).
- Opslaan op de bewerkpagina maakt altijd een **nieuwe versie** aan — herstel is eenvoudig uit te breiden.
- Media wordt op schijf/object storage bewaard, nooit in de database.

## Structuur

```
app/
  main.py            # FastAPI entrypoint
  config.py          # Instellingen via env vars
  db.py / models.py  # SQLAlchemy (Client, Submission, Asset, ContentVersion, MagicToken)
  api/               # Routes: telegram-webhook, bewerkpagina, health
  services/          # pipeline, Whisper, herschrijving, foto-optimalisatie, opslag
app/templates/       # Mobiele bewerkpagina (mobile-first)
tests/               # pytest
```

## Volgende stappen (fase 2)

- WhatsApp Business Cloud API-kanaal
- Object storage (Cloudflare R2 / MinIO) i.p.v. lokale disk
- Publicatie naar WordPress via REST API
- E-mail notificaties bij fouten
