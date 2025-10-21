import asyncio, re
from typing import Optional
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from config import TELEGRAM_BOT_TOKEN
from db import (
    init_db, get_or_create_user, log_message, add_feedback, list_faqs,
    get_session, save_session, reset_session
)
from nlu import NLU
from dialog import resolve_slots, handle_intent

MAIN_MENU = [["📚 FAQs", "🗓️ Schedule"], ["⏰ Deadlines", "📝 Feedback"], ["❓Help", "🔄 Reset"]]
nlu: Optional[NLU] = None

def format_faq_list():
    rows = list_faqs()
    if not rows:
        return "No FAQs available yet."
    top10 = rows[:10]
    lines = ["📚 Sample FAQs:"]
    for r in top10:
        lines.append(f"• {r.question}")
    return "\n".join(lines)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = get_or_create_user(user.id, user.first_name or "", user.last_name or "", user.username or "")
    reset_session(uid)
    log_message(uid, "in", "/start", "start", 1.0)
    text = (
        "Hi, I'm your educational assistant 🤖\n"
        "I can help with course schedules, assignment deadlines, enrollment, tuition, and contacts.\n"
        "I support multi-turn dialogue. For example, you can ask about a course first and then just say “A1 deadline?”\n\n"
        "Send “🔄 Reset” anytime to clear context."
    )
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = get_or_create_user(user.id, user.first_name or "", user.last_name or "", user.username or "")
    log_message(uid, "in", "/help", "help", 1.0)
    text = (
        "Multi-turn example:\n"
        "You: 158.780 what's this week?\n"
        "Bot: returns the schedule\n"
        "You: A1 deadline?\n"
        "Bot: uses the remembered course to answer directly\n\n"
        "Commands: /start /help /reset"
    )
    await update.message.reply_text(text)

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = get_or_create_user(user.id, user.first_name or "", user.last_name or "", user.username or "")
    reset_session(uid)
    await update.message.reply_text("Context has been reset.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global nlu
    msg = update.message
    if not msg: return
    user = update.effective_user
    uid = get_or_create_user(user.id, user.first_name or "", user.last_name or "", user.username or "")
    text = (msg.text or "").strip()

    # Menu actions
    if text in ["📚 FAQs", "FAQs", "FAQ", "faqs"]:
        log_message(uid, "in", text, "menu_faq", 1.0)
        await msg.reply_text(format_faq_list()); return
    if text in ["🗓️ Schedule", "Schedule", "schedule"]:
        log_message(uid, "in", text, "menu_schedule", 1.0)
        await msg.reply_text("Please tell me the course code (e.g., 158.780)."); return
    if text in ["⏰ Deadlines", "Deadlines", "Deadline", "deadline"]:
        log_message(uid, "in", text, "menu_deadline", 1.0)
        await msg.reply_text("Please tell me the course code and assignment (e.g., 158.780 A1)."); return
    if text in ["❓Help", "Help", "/help"]:
        await help_cmd(update, context); return
    if text in ["🔄 Reset", "/reset"]:
        await reset_cmd(update, context); return

    # Feedback pattern: "<rating 1-5> <comment>"
    if m := re.match(r"^\s*([1-5])\s+(.+)$", text):
        rating, comment = int(m.group(1)), m.group(2)
        add_feedback(uid, None, rating, comment)
        log_message(uid, "in", text, "feedback", 1.0)
        await msg.reply_text("Thanks! Your feedback has been recorded. 🙏")
        return

    # NLU
    if nlu is None:
        nlu = NLU()
    intent, faq_id, conf, ents = nlu.analyze(text)
    mid = log_message(uid, "in", text, intent, conf)

    # Load session context
    ctx = get_session(uid)

    # Direct FAQ answer if matched
    if intent == "faq" and faq_id is not None:
        rows = list_faqs()
        faq_map = {int(r.id): r for r in rows}
        r = faq_map.get(faq_id)
        answer = r.answer if r else "Sorry, I couldn't find a suitable answer."
        log_message(uid, "out", answer, "faq", conf)
        await msg.reply_text(f"[Possible answer] (confidence {conf:.2f})\n{answer}")
        # Lightly update last-course/assignment if extracted
        if ents.get("course"): ctx["last_course"] = ents["course"]
        if ents.get("assignment"): ctx["last_assignment"] = ents["assignment"]
        save_session(uid, ctx)
        return

    # Business intents or continuation via pending_intent
    current_intent = intent or ctx.get("pending_intent")
    if current_intent in ["schedule", "deadline"]:
        merged_slots, missing, prompt = resolve_slots(ctx, current_intent, ents)
        if missing:
            # Persist pending intent and partial slots
            ctx["pending_intent"] = current_intent
            ctx["slots"] = merged_slots
            save_session(uid, ctx)
            log_message(uid, "out", prompt, "ask_slot", 1.0)
            await msg.reply_text(prompt); return
        # All slots are ready; execute
        reply = handle_intent(ctx, current_intent, merged_slots)
        log_message(uid, "out", reply, current_intent, 1.0)
        await msg.reply_text(reply)
        # Update memory
        if merged_slots.get("course"): ctx["last_course"] = merged_slots["course"]
        if merged_slots.get("assignment"): ctx["last_assignment"] = merged_slots["assignment"]
        # Clear pending intent/slots for a fresh turn next time
        ctx["pending_intent"] = None
        ctx["slots"] = {}
        save_session(uid, ctx)
        return

    # If we have entities but no intent, try guiding the user
    if ents.get("course") or ents.get("assignment"):
        if ents.get("course") and not ents.get("assignment"):
            ctx["last_course"] = ents["course"]
            ctx["pending_intent"] = None
            ctx["slots"] = {}
            save_session(uid, ctx)
            reply = ("Course code received. Do you want the schedule 🗓️ or an assignment deadline ⏰?\n"
                     "Reply with “Schedule” or “Deadlines”, or ask directly like “A1 deadline?”.")
            log_message(uid, "out", reply, "clarify_next", 1.0)
            await msg.reply_text(reply); return
        if ents.get("assignment") and ctx.get("last_course"):
            # Auto-convert to a deadline query
            current_intent = "deadline"
            merged_slots, missing, prompt = resolve_slots(ctx, current_intent, ents)
            if missing:
                ctx["pending_intent"] = current_intent
                ctx["slots"] = merged_slots
                save_session(uid, ctx)
                await msg.reply_text(prompt); return
            reply = handle_intent(ctx, current_intent, merged_slots)
            log_message(uid, "out", reply, current_intent, 1.0)
            await msg.reply_text(reply)
            if merged_slots.get("assignment"): ctx["last_assignment"] = merged_slots["assignment"]
            ctx["pending_intent"] = None
            ctx["slots"] = {}
            save_session(uid, ctx)
            return

    # Fallback
    fallback = (
        "I didn't fully understand that 🤔\n"
        "• Try “Schedule” or “Deadlines”\n"
        "• Or ask directly: 158.780 A1 deadline?\n"
        "• Send “FAQs” to see examples."
    )
    log_message(uid, "out", fallback, "fallback", 0.0)
    await msg.reply_text(fallback)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Exception: {context.error}")

# --- keep all your imports and handlers above unchanged ---

def main():
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)
    # IMPORTANT: synchronous/blocking; no asyncio.run needed
    app.run_polling()  # remove close_loop, no await here

if __name__ == "__main__":
    main()

