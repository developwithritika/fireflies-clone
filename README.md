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

## API

- `GET /api/v1/meetings?search=&participant=&sort=` - list/search/filter meetings
- `POST /api/v1/meetings` - create a meeting with transcript, summary and action items
- `GET /api/v1/meetings/{id}` - meeting detail
- `DELETE /api/v1/meetings/{id}` - remove a meeting and dependent data
- `GET /api/v1/meetings/{id}/transcript?skip=&limit=` - ordered transcript
- `PUT /api/v1/action-items/{id}` - toggle an action item

## Assumptions and constraints

The app is intentionally single-user. Authentication, live meeting bots, real transcription, and generated AI output are out of scope; summary data is seeded/mocked. A transcript is represented by timestamped lines so it can be paged and synchronized efficiently with media. SQLite is used for the assignment and the SQLAlchemy data layer can be migrated to PostgreSQL.

## Project layout

```
backend/     FastAPI REST API, SQLite models and seed data
frontend/    Next.js dashboard and meeting detail experience
```
