import os
from pathlib import Path

import dotenv
dotenv.load_dotenv()


# Telegram token
TOKEN = os.getenv("TOKEN")
# Path to project folder
BASE_DIR = Path("__file__").parent.parent.absolute()
# Path to stickers folder
STICKERS_DIR = os.path.join(BASE_DIR, "stickers")
# Path to telegram server
URL = "https://api.telegram.org/file/bot{TOKEN}/{file_path}"
