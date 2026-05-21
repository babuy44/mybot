import os
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8803386602:AAHvBUG9rZ_23Rt0UQK7rN11ExFryv0JHzY"
YOUR_ID = 1663746192
DATA_FILE = "balances.json"

def load_balances():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_balances(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton("📤 Отправить", callback_data="send")],
        [InlineKeyboardButton("⚡ В стек", callback_data="stack")]
    ]
    await update.message.reply_text("🏦 Кошелёк", reply_markup=InlineKeyboardMarkup(keyboard))

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    bal = load_balances().get(user_id, 0)
    await query.edit_message_text(f"💰 Баланс: {bal} USDT")

async def send_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting"] = "amount"
    await query.edit_message_text("💰 Введите сумму:")

async def stack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting"] = "stack_amount"
    await query.edit_message_text("💰 Введите сумму для отправки в стек:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting") == "amount":
        try:
            amount = float(update.message.text)
            user_id = str(update.message.from_user.id)
            bal = load_balances().get(user_id, 0)
            if amount > bal:
                await update.message.reply_text("❌ Недостаточно средств")
            else:
                data = load_balances()
                data[user_id] = bal - amount
                save_balances(data)
                await update.message.reply_text(f"✅ Отправлено {amount} USDT")
            context.user_data.pop("awaiting")
        except:
            await update.message.reply_text("❌ Ошибка")
    elif context.user_data.get("awaiting") == "stack_amount":
        try:
            amount = float(update.message.text)
            user_id = str(update.message.from_user.id)
            bal = load_balances().get(user_id, 0)
            if amount > bal:
                await update.message.reply_text("❌ Недостаточно средств")
            else:
                data = load_balances()
                data[user_id] = bal - amount
                save_balances(data)
                await update.message.reply_text(f"✅ Отправлено {amount} USDT на адрес бурмалда")
            context.user_data.pop("awaiting")
        except:
            await update.message.reply_text("❌ Ошибка")

async def set_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != YOUR_ID:
        await update.message.reply_text("⛔ Нет доступа")
        return
    try:
        uid = str(context.args[0])
        val = float(context.args[1])
        data = load_balances()
        data[uid] = val
        save_balances(data)
        await update.message.reply_text(f"✅ Баланс {uid} = {val}")
    except:
        await update.message.reply_text("❌ /setbalance ID сумма")

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != YOUR_ID:
        return
    try:
        uid = str(context.args[0])
        amount = float(context.args[1])
        data = load_balances()
        data[uid] = data.get(uid, 0) + amount
        save_balances(data)
        await update.message.reply_text(f"✅ Добавлено {amount} USDT для {uid}")
    except:
        await update.message.reply_text("❌ /addbalance ID сумма")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setbalance", set_balance))
    app.add_handler(CommandHandler("addbalance", add_balance))
    app.add_handler(CallbackQueryHandler(balance, pattern="balance"))
    app.add_handler(CallbackQueryHandler(send_start, pattern="send"))
    app.add_handler(CallbackQueryHandler(stack_start, pattern="stack"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
