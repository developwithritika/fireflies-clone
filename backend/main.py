from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
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
    title: Mapped[str] = mapped_column(String, index=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    media_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    participants: Mapped[list[Participant]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    transcript_lines: Mapped[list[TranscriptLine]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    summary: Mapped[Optional[Summary]] = relationship(back_populates="meeting", cascade="all, delete-orphan", uselist=False)
    action_items: Mapped[list[ActionItem]] = relationship(back_populates="meeting", cascade="all, delete-orphan")


class Participant(Base):
    __tablename__ = "participants"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    meeting: Mapped[Meeting] = relationship(back_populates="participants")


class TranscriptLine(Base):
    __tablename__ = "transcript_lines"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    speaker: Mapped[str] = mapped_column(String)
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
    speaker: str
    start_time_ms: int = Field(ge=0)
    end_time_ms: int = Field(ge=0)
    text: str


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


class ActionItemUpdate(BaseModel):
    is_completed: bool


class MeetingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    date: datetime
    duration_seconds: int
    participants: list[str]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def detail(meeting: Meeting) -> dict:
    return {"id": meeting.id, "title": meeting.title, "date": meeting.date, "duration_seconds": meeting.duration_seconds,
            "media_url": meeting.media_url, "participants": [p.name for p in meeting.participants],
            "summary": None if not meeting.summary else {"content": meeting.summary.content, "key_topics": meeting.summary.key_topics.split(",") if meeting.summary.key_topics else []},
            "action_items": [{"id": a.id, "description": a.description, "is_completed": a.is_completed} for a in meeting.action_items]}


app = FastAPI(title="Fireflies Clone API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])
Base.metadata.create_all(bind=engine)


@app.get("/health")
def health(): return {"status": "ok"}


@app.get("/api/v1/meetings")
def list_meetings(search: str = "", participant: str = "", sort: str = Query("newest", pattern="^(newest|oldest|title)$"), db: Session = Depends(get_db)):
    query = db.query(Meeting)
    if search:
        query = query.filter(or_(Meeting.title.ilike(f"%{search}%"), Meeting.transcript_lines.any(TranscriptLine.text.ilike(f"%{search}%"))))
    if participant:
        query = query.filter(Meeting.participants.any(Participant.name == participant))
    query = query.order_by(Meeting.title.asc() if sort == "title" else Meeting.date.asc() if sort == "oldest" else Meeting.date.desc())
    return [{"id": m.id, "title": m.title, "date": m.date, "duration_seconds": m.duration_seconds, "participants": [p.name for p in m.participants]} for m in query.all()]


@app.post("/api/v1/meetings", status_code=201)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db)):
    if any(line.end_time_ms < line.start_time_ms for line in payload.transcript):
        raise HTTPException(422, "Transcript end time must follow start time")
    m = Meeting(title=payload.title, date=payload.date, duration_seconds=payload.duration_seconds, media_url=payload.media_url)
    m.participants = [Participant(name=name.strip()) for name in payload.participants if name.strip()]
    m.transcript_lines = [TranscriptLine(**line.model_dump()) for line in payload.transcript]
    if payload.summary: m.summary = Summary(content=payload.summary, key_topics=",".join(payload.key_topics))
    m.action_items = [ActionItem(description=text) for text in payload.action_items if text.strip()]
    db.add(m); db.commit(); db.refresh(m)
    return detail(m)


@app.get("/api/v1/meetings/{meeting_id}")
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    m = db.get(Meeting, meeting_id)
    if not m: raise HTTPException(404, "Meeting not found")
    return detail(m)


@app.delete("/api/v1/meetings/{meeting_id}", status_code=204)
def delete_meeting(meeting_id: str, db: Session = Depends(get_db)):
    m = db.get(Meeting, meeting_id)
    if not m: raise HTTPException(404, "Meeting not found")
    db.delete(m); db.commit()


@app.get("/api/v1/meetings/{meeting_id}/transcript")
def transcript(meeting_id: str, skip: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=1000), db: Session = Depends(get_db)):
    if not db.get(Meeting, meeting_id): raise HTTPException(404, "Meeting not found")
    return db.query(TranscriptLine).filter_by(meeting_id=meeting_id).order_by(TranscriptLine.start_time_ms).offset(skip).limit(limit).all()


@app.put("/api/v1/action-items/{action_item_id}")
def update_action_item(action_item_id: str, payload: ActionItemUpdate, db: Session = Depends(get_db)):
    item = db.get(ActionItem, action_item_id)
    if not item: raise HTTPException(404, "Action item not found")
    item.is_completed = payload.is_completed; db.commit(); db.refresh(item)
    return {"id": item.id, "description": item.description, "is_completed": item.is_completed}
