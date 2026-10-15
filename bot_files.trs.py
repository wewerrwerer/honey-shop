import asyncio
import time
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ==================== НАЛАШТУВАННЯ ====================
TOKEN = "8584870036:AAExkst_o8bc-eSO4KXgLJihmDB9blasp2Q"
ADMIN_ID = -1004300682493  
# ======================================================

bot = Bot(token=TOKEN)
dp = Dispatcher()

def init_db():
    conn = sqlite3.connect("cyber_guard.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            user_id INTEGER PRIMARY KEY,
            warn_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_warns(user_id: int) -> int:
    conn = sqlite3.connect("cyber_guard.db")
    cursor = conn.cursor()
    cursor.execute("SELECT warn_count FROM warns WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def add_warn(user_id: int) -> int:
    conn = sqlite3.connect("cyber_guard.db")
    cursor = conn.cursor()
    current = get_warns(user_id) + 1
    cursor.execute("INSERT OR REPLACE INTO warns (user_id, warn_count) VALUES (?, ?)", (user_id, current))
    conn.commit()
    conn.close()
    return current

def reset_warns(user_id: int):
    conn = sqlite3.connect("cyber_guard.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM warns WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

pending_users = {}
flood_db = {}

SPAM_DOMAINS = ["http://", "https://", "t.me/", "www.", ".com", ".ua", "bit.ly", "t.me/joinchat"]
BAD_WORDS = ["спам", "заробіток", "скам", "крипта", "робота в інтернеті"]

@dp.message(F.new_chat_members)
async def pro_welcome(message: Message):
    for user in message.new_chat_members:
        if user.id == bot.id:
            continue
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Натисніть, щоб підтвердити, що ви людина", callback_data=f"verify_{user.id}")]
        ])
        
        try:
            warning_msg = await message.answer(
                f"🛡 **УЛЬТРА-СИСТЕМА БЕЗПЕКИ (РІВЕНЬ 1000%)**\n\n"
                f"Вітаю, {user.full_name}! У вас є рівно **60 секунд**, щоб довести, що ви не бот, інакше система вас заблокує.",
                reply_markup=keyboard
            )
            
            pending_users[user.id] = {
                "chat_id": message.chat.id,
                "msg_id": warning_msg.message_id
            }
            
            asyncio.create_task(kick_unverified_task(user.id, message.chat.id, warning_msg.message_id))
            
        except Exception as e:
            print(f"Помилка створення капчі: {e}")

async def kick_unverified_task(user_id: int, chat_id: int, msg_id: int):
    await asyncio.sleep(60)
    if user_id in pending_users:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            
            await bot.send_message(ADMIN_ID, f"🚨 **АВТО-КІК (Капча):** Користувача не верифіковано (ID: `{user_id}`). Вигнано.")
            del pending_users[user_id]
        except Exception as e:
            print(f"Помилка авто-кіку: {e}")

@dp.callback_query(F.data.startswith("verify_"))
async def verify_callback(callback: CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    
    if callback.from_user.id == target_user_id:
        if target_user_id in pending_users:
            del pending_users[target_user_id]
            await callback.message.delete()
            await callback.answer("✅ Верифікацію успішно пройдено!", show_alert=True)
    else:
        await callback.answer("❌ Це кнопка не для вас!", show_alert=True)

@dp.message(F.text)
async def pro_filter(message: Message):
    if not message.from_user:
        return
        
    user_id = message.from_user.id
    text_lower = message.text.lower()
    
    is_spam = any(domain in text_lower for domain in SPAM_DOMAINS)
    is_bad = any(word in text_lower for word in BAD_WORDS)
    
    now = time.time()
    if user_id not in flood_db:
        flood_db[user_id] = []
    flood_db[user_id] = [t for t in flood_db[user_id] if now - t < 5]
    flood_db[user_id].append(now)
    
    is_flood = len(flood_db[user_id]) > 4

    if is_spam or is_bad or is_flood:
        try:
            await message.delete()
        except Exception:
            pass
            
        current_warns = add_warn(user_id)
        reason = "Флуд повідомленнями" if is_flood else "Заборонені слова або посилання"
        
        if current_warns >= 3:
            try:
                await message.chat.ban(user_id)
                await message.chat.unban(user_id)
                reset_warns(user_id)
                
                await bot.send_message(
                    ADMIN_ID,
                    f"⛔️ **УЛЬТРА-БАН (3/3 ВАРНІВ у БД):**\n"
                    f"👤 Користувач: {message.from_user.full_name} (`{user_id}`)\n"
                    f"📝 Причина: {reason}"
                )
            except Exception as e:
                print(f"Помилка бану: {e}")
        else:
            warn_msg = await message.answer(
                f"⚠️ {message.from_user.full_name}, ваше повідомлення видалено!\n"
                f"📌 Причина: _{reason}_\n"
                f"⚠️ Попередження (у базі): **{current_warns}/3** (при досягненні 3 — бан)."
            )
            await asyncio.sleep(5)
            try:
                await warn_msg.delete()
            except:
                pass

async def main():
    print("🚀 УЛЬТРА-ОХОРОНЕЦЬ НА 1000% (БАЗА ДАНИХ ACTIVE) ЗАПУЩЕНИЙ...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
