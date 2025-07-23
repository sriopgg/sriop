
import os
from typing import List

# Bot Configuration
API_TOKEN = os.getenv("API_TOKEN", "8163091559:AAEUU-W7lpahXzdNaoyIzLAstP8I76xqPlI")

# Admin Configuration
ADMIN_ID = int(os.getenv("ADMIN_ID", "7589375459"))
ADMINS: List[int] = [ADMIN_ID]  # Can add more admin IDs

# Payment Configuration
SIGN_PRICE_TRX = float(os.getenv("SIGN_PRICE_TRX", "3.0"))
TRX_ADDRESS = os.getenv("TRX_ADDRESS", "TKz2yJFyWMuNKJAJikm9EbEv9Hspyr3niH")

# File Configuration
TEMP_DIR = "temp"
SIGNED_DIR = "signed"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Database Configuration
DB_PATH = "bot_database.db"

# Logging Configuration
LOG_LEVEL = "INFO"
