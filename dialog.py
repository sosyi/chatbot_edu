from typing import Dict, Optional, Tuple
from db import get_schedule_by_course, get_deadline

# Slot requirements per intent
REQUIRED_SLOTS = {
    "schedule": ["course"],
    "deadline": ["course", "assignment"]
}

def resolve_slots(ctx: Dict, intent: str, new_slots: Dict[str, Optional[str]]) -> Tuple[Dict, Dict, Optional[str]]:
    """
    Merge newly extracted entities into session slots and check missing ones.

    Returns:
      (merged_slots, missing_slots_dict, prompt_text_if_missing)
    """
    slots = ctx.get("slots", {}).copy()

    # Inherit last known course/assignment if user omitted them this turn
    if not new_slots.get("course") and ctx.get("last_course"):
        new_slots["course"] = ctx["last_course"]
    if not new_slots.get("assignment") and ctx.get("last_assignment"):
        new_slots["assignment"] = ctx["last_assignment"]

    # Merge new values
    for k, v in new_slots.items():
        if v:
            slots[k] = v

    # Compute missing
    missing = [s for s in REQUIRED_SLOTS.get(intent, []) if not slots.get(s)]
    if missing:
        if missing == ["course"]:
            return slots, {"course": None}, "Please tell me the course code (e.g., 158.780)."
        if missing == ["assignment"]:
            return slots, {"assignment": None}, "Please tell me the assignment name (e.g., A1)."
        if set(missing) == {"course", "assignment"}:
            return (
                slots,
                {"course": None, "assignment": None},
                "Please provide the course code (e.g., 158.780) and assignment (e.g., A1)."
            )
    return slots, {}, None

def handle_intent(ctx: Dict, intent: str, slots: Dict) -> str:
    """
    Execute the business logic after all slots are filled and return the response text.
    Also: caller should persist last_course/last_assignment if present.
    """
    course = slots.get("course")
    assignment = slots.get("assignment")

    if intent == "schedule":
        data = get_schedule_by_course(course)
        if data:
            return f"Schedule for {course}:\n• {data['title']}\n{data['details']}"
        return f"I don't have schedule data for {course} yet. Please check the official announcement or contact the coordinator."

    if intent == "deadline":
        data = get_deadline(course, assignment)
        if data:
            return f"Deadline for {course} {assignment}: {data['due_at']}\nSubmit via: {data['submit_to']}"
        return f"I don't have a deadline record for {course} {assignment}. Please follow the course outline/announcement."

    return "Let me double-check that."
