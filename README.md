# Foreign Client Engine

A web application for discovering foreign business prospects, auditing websites, enriching public contact details, scoring opportunities, generating outreach drafts, and managing Gmail drafts/sending.

## Architecture

- Frontend: React + Vite
- Backend: FastAPI
- Database: SQLAlchemy
- Lead discovery: OpenStreetMap Nominatim + Overpass
- Contact enrichment: public information from official business websites
- Outreach: rule-based personalized drafts
- Gmail: OAuth 2.0 for drafts and sending

## Production deployment

### Frontend

Deploy the `frontend` directory as the Vercel project root.

Set:

`VITE_API_URL=https://foreign-client-engine.onrender.com`

Do not commit frontend `.env` files. Use Vercel environment variables instead.

### Backend

Run:

`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Required environment variables for Gmail:

- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REDIRECT_URI`
- `FRONTEND_URL`

The Gmail redirect URI must exactly match the URI configured in Google Cloud.

## Important production note

The current application uses SQLite for local development. A persistent production deployment should use a managed PostgreSQL database and set a database URL through the environment rather than relying on a writable local filesystem.

## Safety

Lead discovery and email generation are intended to assist research and drafting. Review generated outreach before sending. Do not represent automated website checks as definitive legal, SEO, accessibility, or performance audits.
