import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8311177614:AAGa_81VEf6EaUe3uCYKongZPj93vuueQX0")

# SQLite file path
DB_PATH = os.getenv("DB_PATH", "db/edu_chatbot.db")

# Similarity threshold for FAQ matching (0~1)
FAQ_SIM_THRESHOLD = float(os.getenv("FAQ_SIM_THRESHOLD", "0.33"))

# Admin usernames (optional, for future features like escalation)
ADMIN_USERNAMES = [u.strip() for u in os.getenv("ADMIN_USERNAMES", "").split(",") if u.strip()]
