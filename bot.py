from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime, timedelta
import json
import os
from os import getenv

DATA_FILE = 'notes_data.json'
MAX_MESSAGES = 10

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    data = load_data()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {'notes': [], 'reset_date': (datetime.now() + timedelta(days=1)).isoformat()}
        save_data(data)
    return data[user_id]

def reset_if_needed(user_id):
    data = load_data()
    user_id = str(user_id)
    user_data = get_user_data(user_id)
    
    reset_date = datetime.fromisoformat(user_data['reset_date'])
    if datetime.now() >= reset_date:
        user_data['notes'] = []
        user_data['reset_date'] = (datetime.now() + timedelta(days=1)).isoformat()
        data[user_id] = user_data
        save_data(data)
    
    return user_data

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Бот для заметок\n\n"
        "Отправьте сообщение - оно сохранится как заметка.\n"
        "Лимит: 10 сообщений в сутки.\n\n"
        "/notes - посмотреть все заметки\n"
        "/delete - удалить заметку"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = reset_if_needed(user_id)
    
    if len(user_data['notes']) >= MAX_MESSAGES:
        await update.message.delete()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Лимит исчерпан! Осталось: 0/{MAX_MESSAGES}\n"
                 f"Удалите заметку через /delete и отправьте сообщение повторно."
        )
        return
    
    note = {
        'id': len(user_data['notes']) + 1,
        'text': update.message.text,
        'date': datetime.now().isoformat()
    }
    
    user_data['notes'].append(note)
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)
    
    remaining = MAX_MESSAGES - len(user_data['notes'])
    await update.message.reply_text(
        f"✅ Заметка сохранена!\n"
        f"Осталось сообщений: {remaining}/{MAX_MESSAGES}"
    )

async def show_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = reset_if_needed(user_id)
    
    if not user_data['notes']:
        await update.message.reply_text("📭 У вас нет заметок.")
        return
    
    text = f"📝 Ваши заметки ({len(user_data['notes'])}/{MAX_MESSAGES}):\n\n"
    for note in user_data['notes']:
        preview = note['text'][:30] + '...' if len(note['text']) > 30 else note['text']
        text += f"{note['id']}. {preview}\n"
    
    await update.message.reply_text(text)

async def delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = reset_if_needed(user_id)
    
    if not user_data['notes']:
        await update.message.reply_text("📭 У вас нет заметок для удаления.")
        return
    
    keyboard = []
    for note in user_data['notes']:
        preview = note['text'][:25] + '...' if len(note['text']) > 25 else note['text']
        keyboard.append([InlineKeyboardButton(f"{note['id']}. {preview}", callback_data=f"del_{note['id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🗑 Выберите заметку для удаления:", reply_markup=reply_markup)

async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    note_id = int(query.data.split('_')[1])
    
    data = load_data()
    user_data = data[str(user_id)]
    
    user_data['notes'] = [n for n in user_data['notes'] if n['id'] != note_id]
    
    for i, note in enumerate(user_data['notes'], 1):
        note['id'] = i
    
    data[str(user_id)] = user_data
    save_data(data)
    
    remaining = MAX_MESSAGES - len(user_data['notes'])
    await query.edit_message_text(
        f"✅ Заметка удалена!\n"
        f"Осталось сообщений: {remaining}/{MAX_MESSAGES}"
    )

def main():
    TOKEN = getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("notes", show_notes))
    app.add_handler(CommandHandler("delete", delete_menu))
    app.add_handler(CallbackQueryHandler(delete_callback, pattern='^del_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Бот запущен...")
    app.run_polling()

if __name__ == '__main__':
    main()
