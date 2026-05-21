import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ⚠️ ВСТАВЬТЕ НОВЫЙ ТОКЕН (получите через /newtoken в @BotFather)
TOKEN = "8803386602:AAG2gBQ7GVcZuysFPbU_NFxYTTbwVBawM4c"

YOUR_ID = 1663746192
DATA_FILE = 'balances.json'

def load_balances():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_balances(balances):
    with open(DATA_FILE, 'w') as f:
        json.dump(balances, f, indent=4)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Мой баланс", callback_data='balance')],
        [InlineKeyboardButton("📤 Отправить вручную", callback_data='send_manual')],
        [InlineKeyboardButton("⚡ Отправить в стек", callback_data='send_stack')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🏦 *Трейдинг Кошелёк*\nВыберите действие:"
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    balances = load_balances()
    balance = balances.get(user_id, 0)
    text = f"💎 *Ваш баланс:* `{balance}` USDT\n\n🆔 ID: `{user_id}`"
    keyboard = [[InlineKeyboardButton("◀ На главную", callback_data='main_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def send_manual_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_address'] = True
    keyboard = [[InlineKeyboardButton("◀ На главную", callback_data='main_menu')]]
    await query.edit_message_text("✍️ *Введите крипто-адрес получателя:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_manual_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_address'):
        address = update.message.text.strip()
        context.user_data['send_address'] = address
        context.user_data['awaiting_address'] = False
        context.user_data['awaiting_amount'] = True
        await update.message.reply_text(f"📡 *Адрес получен:*\n`{address}`\n\n💰 *Введите сумму в USDT:*", parse_mode='Markdown')

async def send_stack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['send_address'] = "бурмалда"
    context.user_data['awaiting_amount'] = True
    await query.edit_message_text(f"📡 *Стек-адрес:* `бурмалда`\n\n💰 *Введите сумму в USDT:*", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ На главную", callback_data='main_menu')]]), parse_mode='Markdown')

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_amount'):
        try:
            amount = float(update.message.text.replace(',', '.'))
            if amount <= 0:
                raise ValueError
            user_id = str(update.message.from_user.id)
            balances = load_balances()
            current_balance = balances.get(user_id, 0)
            if amount > current_balance:
                await update.message.reply_text(f"❌ *Недостаточно средств!*\nВаш баланс: `{current_balance}` USDT", parse_mode='Markdown')
            else:
                balances[user_id] = current_balance - amount
                save_balances(balances)
                address = context.user_data.get('send_address', 'неизвестно')
                import random
                txid = ''.join(random.choices('0123456789abcdef', k=16))
                await update.message.reply_text(f"✅ *Отправлено!*\n\n📤 Сумма: `{amount}` USDT\n📍 Адрес: `{address}`\n🆔 Транзакция: `{txid}`\n\n⚠️ *Демо-режим*", parse_mode='Markdown')
            context.user_data.pop('awaiting_amount', None)
            context.user_data.pop('send_address', None)
            keyboard = [[InlineKeyboardButton("💰 Мой баланс", callback_data='balance')], [InlineKeyboardButton("📤 Отправить вручную", callback_data='send_manual')], [InlineKeyboardButton("⚡ Отправить в стек", callback_data='send_stack')]]
            await update.message.reply_text("🏦 Главное меню:", reply_markup=InlineKeyboardMarkup(keyboard))
        except ValueError:
            await update.message.reply_text("❌ Введите число")

async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("💰 Мой баланс", callback_data='balance')], [InlineKeyboardButton("📤 Отправить вручную", callback_data='send_manual')], [InlineKeyboardButton("⚡ Отправить в стек", callback_data='send_stack')]]
    await query.edit_message_text("🏦 *Трейдинг Кошелёк*\nВыберите действие:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def set_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != YOUR_ID:
        await update.message.reply_text("⛔ Доступ запрещён.")
        return
    try:
        user_id = str(context.args[0])
        new_balance = float(context.args[1])
        balances = load_balances()
        balances[user_id] = new_balance
        save_balances(balances)
        await update.message.reply_text(f"✅ Баланс {user_id} → {new_balance} USDT")
    except:
        await update.message.reply_text("❌ /setbalance [user_id] [сумма]")

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != YOUR_ID:
        return
    try:
        user_id = str(context.args[0])
        amount = float(context.args[1])
        balances = load_balances()
        balances[user_id] = balances.get(user_id, 0) + amount
        save_balances(balances)
        await update.message.reply_text(f"✅ Добавлено {amount} USDT для {user_id}")
    except:
        await update.message.reply_text("❌ /addbalance [user_id] [сумма]")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", main_menu))
    app.add_handler(CommandHandler("setbalance", set_balance))
    app.add_handler(CommandHandler("addbalance", add_balance))
    app.add_handler(CallbackQueryHandler(show_balance, pattern='^balance$'))
    app.add_handler(CallbackQueryHandler(send_manual_start, pattern='^send_manual$'))
    app.add_handler(CallbackQueryHandler(send_stack_start, pattern='^send_stack$'))
    app.add_handler(CallbackQueryHandler(back_to_main_menu, pattern='^main_menu$'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_address))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))
    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
