from datetime import datetime, timedelta
from main import ActionItem, Meeting, Participant, SessionLocal, Summary, TranscriptLine

db = SessionLocal()
if not db.query(Meeting).count():
    samples = [
        ("Product roadmap sync", ["Ritika", "Maya", "Sam"], "Aligned the Q3 roadmap around customer onboarding and reporting.", ["onboarding", "Q3 planning", "reporting"], ["Ritika to share revised roadmap", "Maya to validate onboarding metrics"]),
        ("Weekly engineering standup", ["Ritika", "Aarav", "Nina"], "The team reviewed sprint progress and identified one release blocker.", ["sprint", "release", "engineering"], ["Aarav to fix the migration issue", "Nina to update release notes"]),
        ("Customer discovery: Acme", ["Ritika", "Jordan Lee"], "Acme needs better visibility into action items after cross-functional calls.", ["customer research", "action items"], ["Send Acme the prototype", "Schedule a follow-up next week"]),
    ]
    for n, (title, people, text, topics, tasks) in enumerate(samples):
        m = Meeting(title=title, date=datetime.utcnow() - timedelta(days=n), duration_seconds=1800 + n * 900, media_url=None)
        m.participants = [Participant(name=p) for p in people]
        m.summary = Summary(content=text, key_topics=",".join(topics))
        m.action_items = [ActionItem(description=t) for t in tasks]
        m.transcript_lines = [
            TranscriptLine(speaker=people[0], start_time_ms=0, end_time_ms=7000, text=f"Thanks for joining the {title.lower()}. Let's start with our goals."),
            TranscriptLine(speaker=people[1], start_time_ms=8000, end_time_ms=18000, text="The main theme from last week was improving follow-through and visibility."),
            TranscriptLine(speaker=people[0], start_time_ms=19000, end_time_ms=30000, text=text),
            TranscriptLine(speaker=people[-1], start_time_ms=31000, end_time_ms=42000, text=f"I'll capture the next steps: {tasks[0].lower()}."),
        ]
        db.add(m)
    db.commit()
print("Seeded Fireflies Clone database.")
