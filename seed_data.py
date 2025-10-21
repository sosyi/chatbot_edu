import json
from sqlalchemy import text
from db import init_db, get_engine, upsert_intent

# FAQ seed data (demo content; replace with your real course data)
FAQS = [
    ("What is the schedule for 158.780 this week?",
     "158.780 this week: Topic - LLM reasoning & optimization; lab/tutorial Wed 14:00–16:00 (Lab 3).",
     "schedule, 158.780, timetable"),
    ("When does the exam week start this term?",
     "Exam weeks: weeks 13–14. Refer to the official schedule issued by the school.",
     "exam, schedule"),
    ("When is the deadline for 158.780 A1?",
     "158.780 A1 due: Week 4 Friday 23:59, submit via Stream/student system.",
     "deadline, 158.780"),
    ("Will late submissions be penalized?",
     "Typically 48 hours grace with 10% penalty per day; special cases require prior approval via email.",
     "deadline, late submission"),
    ("How do I change courses during add/drop?",
     "Use the student portal during add/drop. For prerequisite issues, contact the course coordinator.",
     "enrollment, add drop"),
    ("Can tuition be paid in installments?",
     "Some schools support installment or deferment plans. Contact the finance office.",
     "tuition"),
    ("How do I book counseling?",
     "Use the campus health portal for 1:1 sessions; for emergencies call the 24/7 hotline.",
     "service, counseling"),
    ("What's the academic office email?",
     "Academic office: xxx@university.edu; replies Mon–Fri 9:00–17:00.",
     "contact, admin"),
]

# Rule intents (regex; case-insensitive)
INTENTS = {
    "schedule": [r"\b(schedule|timetable|what.*week|this week|class.*when|lecture)\b", r"\b(exam week)\b"],
    "deadline": [r"\b(deadline|due|ddl|late|submission)\b"],
    "enrollment": [r"\b(enroll|enrollment|add/?drop|register|drop)\b"],
    "tuition": [r"\b(tuition|payment|fee)\b"],
    "contact": [r"\b(contact|email|phone)\b"],
}

# Demo business data — schedules
SCHEDULES = [
    ("158.780", "Week 4: LLM Reasoning & Optimization", "Lecture: decoding strategies/cache/throughput;\nTutorial: Wed 14:00–16:00, Lab 3."),
]

# Demo business data — deadlines
DEADLINES = [
    ("158.780", "A1", "Week 4 Friday 23:59", "Stream / student portal"),
    ("158.780", "A2", "Week 8 Friday 23:59", "Stream / student portal"),
]

def seed():
    """Initialize DB and load seed content."""
    init_db()
    eng = get_engine()
    with eng.begin() as conn:
        # FAQs
        conn.execute(text("DELETE FROM faqs"))
        for q, a, tags in FAQS:
            conn.execute(text("INSERT INTO faqs (question, answer, tags) VALUES (:q,:a,:t)"),
                         {"q": q, "a": a, "t": tags})

        # Schedules
        conn.execute(text("DELETE FROM schedules"))
        for c, title, details in SCHEDULES:
            conn.execute(text("INSERT INTO schedules (course_code, title, details) VALUES (:c,:t,:d)"),
                         {"c": c, "t": title, "d": details})

        # Deadlines
        conn.execute(text("DELETE FROM deadlines"))
        for c, a, due, sub in DEADLINES:
            conn.execute(text("INSERT INTO deadlines (course_code, assignment, due_at, submit_to) VALUES (:c,:a,:du,:s)"),
                         {"c": c, "a": a, "du": due, "s": sub})

    # Intents
    for name, patterns in INTENTS.items():
        upsert_intent(name, json.dumps(patterns, ensure_ascii=False))

    print("✅ Database initialized and seed data loaded.")

if __name__ == "__main__":
    seed()
