import os
from pathlib import Path

# Telegram token
TOKEN = "8863066329:AAGjNr6yKuHCQAz0Astk7Vi-pMzIMJyBlh4"
# Path to project folder
BASE_DIR = Path("__file__").parent.parent.absolute()
# Path to stickers folder
STICKERS_DIR = os.path.join(BASE_DIR, "stickers")
# Path to telegram server
URL = "https://api.telegram.org/file/bot{TOKEN}/{file_path}"
