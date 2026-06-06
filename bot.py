import asyncio
import logging
import os
import json
from datetime import datetime
from threading import Thread

from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from flask import Flask, request, jsonify

# ====================== НАСТРОЙКИ ======================
API_ID = 8
API_HASH = '7245de8e747a0d6fbe11f7cc14fcc0bb'
BOT_TOKEN = '8867073594:AAFf79ATdyNaAJQHtLWedIymQtRof01z1C8'
OWNER_ID = 1663746192
CRYPTO_ADDRESS = '0xYourAddress'
DEFAULT_PERCENT = 0

DATA_FILE = 'bluevault_data.json'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====================== СОХРАНЕНИЕ ДАННЫХ ======================
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('balances', {}), data.get('percent', DEFAULT_PERCENT)
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
    return {}, DEFAULT_PERCENT

def save_data(balances, percent):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'balances': balances,
                'percent': percent,
                'last_updated': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")

user_balances, current_percent = load_data()

# ====================== TELETHON ======================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

bot = TelegramClient(StringSession(), API_ID, API_HASH, loop=loop)
app = Flask(__name__)

_handled = set()

def already_handled(event):
    if event.id in _handled:
        return True
    _handled.add(event.id)
    if len(_handled) > 15000:
        _handled.clear()
    return False

# ====================== FLASK ======================
@app.route('/')
def index():
    return HTML_PAGE

@app.route('/get_balance')
def get_balance():
    user_id = request.args.get('user_id')
    return jsonify({
        'balance': float(user_balances.get(str(user_id), 0)),
        'percent': current_percent
    })

@app.route('/get_address')
def get_address():
    return jsonify({'address': CRYPTO_ADDRESS})

# ====================== HTML СТРАНИЦА (оригинальная) ======================
HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <title>BlueVault</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root { --bg: #0a1628; --card: #0f1f3d; --border: #1a3256; --blue: #2196F3; --blue-light: #64B5F6; --text: #E3F2FD; --text-secondary: #90CAF9; --green: #4CAF50; --red: #EF5350; }
        * { margin: 0
