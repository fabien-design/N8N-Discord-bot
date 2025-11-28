"""
Configuration module for the Discord bot.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Discord Configuration
TOKEN = os.getenv("TOKEN")
PREFIX = "!"

# Intents Configuration
ENABLE_MESSAGE_CONTENT = True
ENABLE_MEMBERS = False
ENABLE_PRESENCES = False

# Allowed User IDs (comma-separated)
ALLOWED_USER_IDS = os.getenv("ALLOWED_USER_IDS")  # e.g., "777910706476679228,1432300772942680075"

# N8N Webhook Configuration
JWT_SECRET = os.getenv("JWT_SECRET")
N8N_WEBHOOK = os.getenv("N8N_WEBHOOK")
