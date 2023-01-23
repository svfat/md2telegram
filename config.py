import os
from pathlib import Path

TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
PORT = int(os.environ.get('PORT', 5000))
DATA_DIR = Path(__file__).parent / 'data'
PAGES_DIR = DATA_DIR / '_pages'
MENUS_DIR = DATA_DIR / '_menus'

HEROKU_APP_NAME = os.environ.get('HEROKU_APP_NAME')