from datetime import datetime, timedelta
from main import ActionItem, Meeting, Participant, SessionLocal, Summary, TranscriptLine

db = SessionLocal()
if not db.query(Meeting).count():
    samples = [
        ("Product roadmap sync", ["Ritika", "Maya", "Sam"], "The team aligned the Q3 roadmap around customer onboarding and reporting.", ["onboarding", "Q3 planning", "reporting"], ["Ritika to share the revised roadmap", "Maya to validate onboarding metrics"]),
        ("Weekly engineering standup", ["Ritika", "Aarav", "Nina"], "The team reviewed sprint progress and identified one release blocker.", ["sprint", "release", "engineering"], ["Aarav to fix the migration issue", "Nina to update the release notes"]),
        ("Customer discovery: Acme", ["Ritika", "Jordan Lee"], "Acme needs better visibility into action items after cross-functional calls.", ["customer research", "action items"], ["Send Acme the prototype", "Schedule a follow-up next week"]),
    ]
    for n, (title, people, summary, topics, tasks) in enumerate(samples):
        meeting = Meeting(title=title, date=datetime.utcnow() - timedelta(days=n), duration_seconds=2700, media_url=None)
        meeting.participants = [Participant(name=person) for person in people]
        meeting.summary = Summary(content=summary, key_topics=",".join(topics))
        meeting.action_items = [ActionItem(description=task) for task in tasks]
        script = [
            (people[0], "Thanks for joining. I want to make sure we leave with clear owners and next steps."),
            (people[1], "I reviewed the notes from our last conversation and grouped the open decisions."),
            (people[0], "The key customer theme is reducing the time between a meeting and a useful follow-up."),
            (people[-1], "We should make the summary easier to scan and give every action item a visible owner."),
            (people[0], summary),
            (people[1], "For the first milestone, I can validate the proposed workflow with a small customer group."),
            (people[-1], "I will document the edge cases and add them to the planning board."),
            (people[0], "Let's keep the initial release focused and measure adoption before expanding scope."),
            (people[1], "That approach gives us a clear feedback loop and keeps the work achievable this sprint."),
            (people[-1], "I'll share the final notes after this call and flag anything that needs a decision."),
            (people[0], f"The immediate follow-up is: {tasks[0].lower()}"),
            (people[0], "Thanks everyone. We will check progress at the next weekly review."),
        ]
        meeting.transcript_lines = [TranscriptLine(speaker=speaker, start_time_ms=index * 15000, end_time_ms=index * 15000 + 13000, text=text) for index, (speaker, text) in enumerate(script)]
        db.add(meeting)
    db.commit()
print("Seeded Fireflies Clone database.")
