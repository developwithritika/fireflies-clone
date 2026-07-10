from __future__ import annotations

import os
from datetime import date, datetime, time
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DATABASE_URL = "sqlite:///./fireflies_clone.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class Meeting(Base):
    __tablename__ = "meetings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(180), index=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    media_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    participants: Mapped[list["Participant"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    transcript_lines: Mapped[list["TranscriptLine"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    summary: Mapped[Optional["Summary"]] = relationship(back_populates="meeting", cascade="all, delete-orphan", uselist=False)
    action_items: Mapped[list["ActionItem"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")


class Participant(Base):
    __tablename__ = "participants"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    meeting: Mapped[Meeting] = relationship(back_populates="participants")


class TranscriptLine(Base):
    __tablename__ = "transcript_lines"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    speaker: Mapped[str] = mapped_column(String(100))
    start_time_ms: Mapped[int] = mapped_column(Integer, index=True)
    end_time_ms: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    meeting: Mapped[Meeting] = relationship(back_populates="transcript_lines")


class Summary(Base):
    __tablename__ = "summaries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), unique=True)
    content: Mapped[str] = mapped_column(Text)
    key_topics: Mapped[str] = mapped_column(Text, default="")
    meeting: Mapped[Meeting] = relationship(back_populates="summary")


class ActionItem(Base):
    __tablename__ = "action_items"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    meeting: Mapped[Meeting] = relationship(back_populates="action_items")


class TranscriptInput(BaseModel):
    speaker: str = Field(min_length=1, max_length=100)
    start_time_ms: int = Field(ge=0)
    end_time_ms: int = Field(ge=0)
    text: str = Field(min_length=1)


class MeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    date: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: int = Field(default=0, ge=0)
    media_url: Optional[str] = None
    participants: list[str] = []
    transcript: list[TranscriptInput] = []
    summary: Optional[str] = None
    key_topics: list[str] = []
    action_items: list[str] = []


class MeetingUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=180)
    date: Optional[datetime] = None
    participants: Optional[list[str]] = None


class ActionItemCreate(BaseModel):
    description: str = Field(min_length=1)


class ActionItemUpdate(BaseModel):
    description: Optional[str] = Field(default=None, min_length=1)
    is_completed: Optional[bool] = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def action_data(item: ActionItem) -> dict:
    return {"id": item.id, "description": item.description, "is_completed": item.is_completed}


def detail(meeting: Meeting) -> dict:
    return {
        "id": meeting.id, "title": meeting.title, "date": meeting.date,
        "duration_seconds": meeting.duration_seconds, "media_url": meeting.media_url,
        "participants": [p.name for p in meeting.participants],
        "summary": None if not meeting.summary else {"content": meeting.summary.content, "key_topics": [x for x in meeting.summary.key_topics.split(",") if x]},
        "action_items": [action_data(a) for a in meeting.action_items],
    }


def require_meeting(db: Session, meeting_id: str) -> Meeting:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    return meeting


app = FastAPI(title="Fireflies Clone API", version="1.1.0")
allowed_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_methods=["*"], allow_headers=["*"])
Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/participants")
def list_participants(db: Session = Depends(get_db)):
    return [row[0] for row in db.query(Participant.name).distinct().order_by(Participant.name).all()]


@app.get("/api/v1/meetings")
def list_meetings(
    search: str = "", participant: str = "", date_from: Optional[date] = None, date_to: Optional[date] = None,
    sort: str = Query("newest", pattern="^(newest|oldest|title)$"), db: Session = Depends(get_db),
):
    query = db.query(Meeting)
    if search:
        query = query.filter(or_(Meeting.title.ilike(f"%{search}%"), Meeting.transcript_lines.any(TranscriptLine.text.ilike(f"%{search}%"))))
    if participant:
        query = query.filter(Meeting.participants.any(Participant.name == participant))
    if date_from:
        query = query.filter(Meeting.date >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(Meeting.date <= datetime.combine(date_to, time.max))
    ordering = Meeting.title.asc() if sort == "title" else Meeting.date.asc() if sort == "oldest" else Meeting.date.desc()
    return [{"id": m.id, "title": m.title, "date": m.date, "duration_seconds": m.duration_seconds, "participants": [p.name for p in m.participants]} for m in query.order_by(ordering).all()]


@app.post("/api/v1/meetings", status_code=201)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db)):
    if any(line.end_time_ms < line.start_time_ms for line in payload.transcript):
        raise HTTPException(422, "Transcript end time must follow start time")
    meeting = Meeting(title=payload.title, date=payload.date, duration_seconds=payload.duration_seconds, media_url=payload.media_url)
    meeting.participants = [Participant(name=name.strip()) for name in payload.participants if name.strip()]
    meeting.transcript_lines = [TranscriptLine(**line.model_dump()) for line in payload.transcript]
    if payload.summary:
        meeting.summary = Summary(content=payload.summary, key_topics=",".join(topic.strip() for topic in payload.key_topics if topic.strip()))
    meeting.action_items = [ActionItem(description=text.strip()) for text in payload.action_items if text.strip()]
    db.add(meeting); db.commit(); db.refresh(meeting)
    return detail(meeting)


@app.get("/api/v1/meetings/{meeting_id}")
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    return detail(require_meeting(db, meeting_id))


@app.put("/api/v1/meetings/{meeting_id}")
def update_meeting(meeting_id: str, payload: MeetingUpdate, db: Session = Depends(get_db)):
    meeting = require_meeting(db, meeting_id)
    if payload.title is not None: meeting.title = payload.title
    if payload.date is not None: meeting.date = payload.date
    if payload.participants is not None:
        meeting.participants = [Participant(name=name.strip()) for name in payload.participants if name.strip()]
    db.commit(); db.refresh(meeting)
    return detail(meeting)


@app.delete("/api/v1/meetings/{meeting_id}", status_code=204)
def delete_meeting(meeting_id: str, db: Session = Depends(get_db)):
    db.delete(require_meeting(db, meeting_id)); db.commit()


@app.get("/api/v1/meetings/{meeting_id}/transcript")
def transcript(meeting_id: str, skip: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=1000), db: Session = Depends(get_db)):
    require_meeting(db, meeting_id)
    return db.query(TranscriptLine).filter_by(meeting_id=meeting_id).order_by(TranscriptLine.start_time_ms).offset(skip).limit(limit).all()


@app.post("/api/v1/meetings/{meeting_id}/action-items", status_code=201)
def create_action_item(meeting_id: str, payload: ActionItemCreate, db: Session = Depends(get_db)):
    require_meeting(db, meeting_id)
    item = ActionItem(meeting_id=meeting_id, description=payload.description)
    db.add(item); db.commit(); db.refresh(item)
    return action_data(item)


@app.put("/api/v1/action-items/{action_item_id}")
def update_action_item(action_item_id: str, payload: ActionItemUpdate, db: Session = Depends(get_db)):
    item = db.get(ActionItem, action_item_id)
    if not item: raise HTTPException(404, "Action item not found")
    if payload.description is not None: item.description = payload.description
    if payload.is_completed is not None: item.is_completed = payload.is_completed
    db.commit(); db.refresh(item)
    return action_data(item)


@app.delete("/api/v1/action-items/{action_item_id}", status_code=204)
def delete_action_item(action_item_id: str, db: Session = Depends(get_db)):
    item = db.get(ActionItem, action_item_id)
    if not item: raise HTTPException(404, "Action item not found")
    db.delete(item); db.commit()
