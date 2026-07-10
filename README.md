# Fireflies Clone

A local-first clone of the Fireflies.ai meeting workspace. It provides a searchable meetings library, interactive timestamped transcripts, playback synchronization, AI-summary placeholders, action items, and meeting CRUD.

## Stack

- **Frontend:** Next.js App Router + TypeScript
- **Backend:** FastAPI + SQLAlchemy
- **Database:** SQLite

## Run locally

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python seed.py
uvicorn main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The frontend expects the API at `http://localhost:8000`; override it with `NEXT_PUBLIC_API_URL` if needed.

## Deploy

The repository includes `render.yaml` for a Render Blueprint deployment of the FastAPI service. After creating it, set `CORS_ORIGINS` to the Vercel deployment URL. Import the same repository into Vercel with `frontend` as the Root Directory, then add `NEXT_PUBLIC_API_URL` using the Render service URL (see `frontend/.env.example`). Redeploy the frontend after setting that variable.

## Architecture

The Next.js App Router frontend calls a REST API hosted by FastAPI. The API owns all persistence and uses SQLAlchemy's relationship and cascade handling to keep meeting data consistent. The dashboard fetches filtered meeting lists; the detail page fetches the meeting metadata and paginated transcript separately. The transcript player is a deterministic mock player, so timestamp seeking and active-line highlighting work without requiring a bundled audio asset.

## Database schema

`meetings` is the parent record (`id`, title, date, duration, optional media URL). It has one-to-many relationships with `participants`, `transcript_lines`, and `action_items`, and a one-to-one relationship with `summaries`. Each transcript row stores the speaker, start/end timestamps, and text; this permits ordered retrieval, full-text searching, and efficient future pagination. Deleting a meeting cascades to all of these dependent rows.

## API

- `GET /api/v1/meetings?search=&participant=&sort=` - list/search/filter meetings
- `POST /api/v1/meetings` - create a meeting with transcript, summary and action items
- `GET /api/v1/meetings/{id}` - meeting detail
- `PUT /api/v1/meetings/{id}` - edit title, participants, or date
- `DELETE /api/v1/meetings/{id}` - remove a meeting and dependent data
- `GET /api/v1/meetings/{id}/transcript?skip=&limit=` - ordered transcript
- `POST /api/v1/meetings/{id}/action-items` - add an action item
- `PUT /api/v1/action-items/{id}` - edit or complete an action item
- `DELETE /api/v1/action-items/{id}` - remove an action item

## Assumptions and constraints

The app is intentionally single-user. Authentication, live meeting bots, real transcription, and generated AI output are out of scope; summary data is seeded/mocked. A transcript is represented by timestamped lines so it can be paged and synchronized efficiently with media. SQLite is used for the assignment and the SQLAlchemy data layer can be migrated to PostgreSQL.

## Project layout

```
backend/     FastAPI REST API, SQLite models and seed data
frontend/    Next.js dashboard and meeting detail experience
```
