# Educational Chatbot (Telegram + Python + SQLite)

## Features
- Multi-turn dialogue with slot filling (course, assignment)
- Rule-based intents (schedule, deadline, enrollment, tuition, contact)
- FAQ semantic retrieval (TF-IDF + cosine similarity)
- Message logging, user feedback, and session persistence
- Easy to extend to webhooks, vector search, and richer data

## Quick Start
1. Python 3.10+
2. `pip install -r requirements.txt`
3. Set `TELEGRAM_BOT_TOKEN` in `.env` or `config.py`
4. `python seed_data.py`
5. `python chatbot_edu.py`

## Notes
- Replace seed data with your real course schedules/deadlines.
- Adjust `FAQ_SIM_THRESHOLD` in `config.py` for recall/precision tradeoffs.
- For production: move from polling to webhook + HTTPS, add monitoring and backups.
# chatbot_edu
# chatbot_edu
