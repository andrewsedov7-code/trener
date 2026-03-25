import asyncio
import json
import logging
import os
from datetime import datetime, date, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import anthropic
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8778445534:AAEKqD5gBAgjg5hvHjRhKFeG8YhZPNrmWB8")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "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")
REMINDER_HOUR = 7   # Во сколько часов присылать напоминание (по UTC+7 Da Nang = UTC+7)
DATA_FILE = "fitbot_data.json"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")
claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ── DATA ──────────────────────────────────────────────────────────────────────
def load_data():
    if Path(DATA_FILE).exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(data, user_id):
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "start_date": date.today().isoformat(),
            "history": [],
            "chat_history": [],
            "streak": 0,
        }
        save_data(data)
    return data[uid]

# ── WORKOUT LOGIC ─────────────────────────────────────────────────────────────
def get_day_number(user):
    start = date.fromisoformat(user["start_date"])
    delta = (date.today() - start).days
    return max(1, delta + 1)

def get_workout(day: int):
    d = day - 1
    return {
        "squats":  30 + d * 2,
        "abs":     30 + d * 2,
        "plank":   60 + d * 5,  # секунды
        "pushups": 10 + d,
    }

def is_today_done(user):
    today = date.today().isoformat()
    return any(h["date"] == today and h["done"] for h in user["history"])

def mark_today(user, done: bool):
    today = date.today().isoformat()
    day = get_day_number(user)
    user["history"] = [h for h in user["history"] if h["date"] != today]
    user["history"].append({"date": today, "done": done, "day": day})

def calc_streak(user):
    streak = 0
    today = date.today()
    for i in range(60):
        d = (today - timedelta(days=i)).isoformat()
        entry = next((h for h in user["history"] if h["date"] == d), None)
        if entry and entry["done"]:
            streak += 1
        elif i > 0:
            break
    return streak

def get_stats_text(user):
    day = get_day_number(user)
    w = get_workout(day)
    streak = calc_streak(user)
    total = sum(1 for h in user["history"] if h["done"])
    today_done = is_today_done(user)

    plank_min = w["plank"] // 60
    plank_sec = w["plank"] % 60
    plank_str = f"{plank_min}м {plank_sec}с" if plank_min else f"{plank_sec}с"

    return (
        f"📊 *Статистика*\n\n"
        f"🗓 День программы: *{day}*\n"
        f"🔥 Серия: *{streak}* дней подряд\n"
        f"✅ Всего тренировок: *{total}*\n"
        f"{'✅ Сегодня выполнено!' if today_done else '⏳ Сегодня ещё не выполнено'}\n\n"
        f"*Сегодняшняя тренировка:*\n"
        f"🦵 Приседания: *{w['squats']}* раз\n"
        f"💪 Пресс: *{w['abs']}* раз\n"
        f"🏋️ Планка: *{plank_str}*\n"
        f"🔥 Отжимания: *{w['pushups']}* раз"
    )

# ── CLAUDE AI ─────────────────────────────────────────────────────────────────
def build_system_prompt(user):
    day = get_day_number(user)
    w = get_workout(day)
    streak = calc_streak(user)
    total = sum(1 for h in user["history"] if h["done"])
    today_done = is_today_done(user)

    return f"""Ты FitBot — персональный фитнес-тренер и мотивационный коуч в Telegram.
Ты помогаешь пользователю тренироваться каждый день к лету. Общайся по-русски.

ТЕКУЩЕЕ СОСТОЯНИЕ:
- День программы: {day}
- Серия (streak): {streak} дней подряд
- Всего выполненных тренировок: {total}
- Сегодня выполнено: {'ДА ✅' if today_done else 'НЕТ ❌'}

СЕГОДНЯШНЯЯ ТРЕНИРОВКА (день {day}):
- Приседания: {w['squats']} раз
- Пресс: {w['abs']} раз  
- Планка: {w['plank']} секунд
- Отжимания: {w['pushups']} раз

ПРАВИЛА ПРОГРАММЫ: +2 к приседаниям и прессу, +5с к планке, +1 отжимание каждый день.

Стиль: энергичный, дружелюбный, с эмодзи. Короткие ответы (2-4 предложения).
Когда пользователь говорит что выполнил тренировку — добавь [MARK_DONE] в конец ответа.
Когда пользователь говорит что пропустил — добавь [MARK_MISSED] в конец.
НЕ показывай маркеры пользователю — только добавляй их в текст."""

async def ask_claude(user, user_message: str) -> tuple[str, bool, bool]:
    """Returns (reply_text, mark_done, mark_missed)"""
    history = user.get("chat_history", [])
    history.append({"role": "user", "content": user_message})

    # Ограничим историю последними 20 сообщениями
    if len(history) > 20:
        history = history[-20:]

    try:
        response = claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=build_system_prompt(user),
            messages=history,
        )
        reply = response.content[0].text

        mark_done = "[MARK_DONE]" in reply
        mark_missed = "[MARK_MISSED]" in reply
        clean_reply = reply.replace("[MARK_DONE]", "").replace("[MARK_MISSED]", "").strip()

        history.append({"role": "assistant", "content": clean_reply})
        user["chat_history"] = history[-20:]

        return clean_reply, mark_done, mark_missed

    except Exception as e:
        logging.error(f"Claude error: {e}")
        return "Ой, не могу подключиться к AI 😔 Попробуй позже!", False, False

# ── KEYBOARD ──────────────────────────────────────────────────────────────────
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Тренировка выполнена!"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="⚡ Мотивируй меня!"), KeyboardButton(text="😔 Пропустил сегодня")],
            [KeyboardButton(text="🏋️ Сегодняшняя тренировка")],
        ],
        resize_keyboard=True,
    )

# ── HANDLERS ──────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    day = get_day_number(user)
    w = get_workout(day)
    save_data(data)

    plank_str = f"{w['plank']}с"
    await message.answer(
        f"🔥 *Привет! Я FitBot — твой тренер к лету!*\n\n"
        f"Сегодня день *{day}* программы.\n\n"
        f"*Твоя тренировка:*\n"
        f"🦵 {w['squats']} приседаний\n"
        f"💪 {w['abs']} пресс\n"
        f"🏋️ {plank_str} планка\n"
        f"🔥 {w['pushups']} отжиманий\n\n"
        f"Каждый день будет чуть сложнее 💪\n"
        f"Я буду присылать напоминание каждое утро в 8:00!\n\n"
        f"Вперёд к лету! 🌞",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )

@dp.message(Command("stats"))
@dp.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    await message.answer(get_stats_text(user), parse_mode="Markdown")

@dp.message(F.text == "🏋️ Сегодняшняя тренировка")
async def cmd_today(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    day = get_day_number(user)
    w = get_workout(day)

    plank_min = w["plank"] // 60
    plank_sec = w["plank"] % 60
    plank_str = f"{plank_min}м {plank_sec}с" if plank_min else f"{w['plank']}с"

    done = is_today_done(user)
    status = "✅ *Уже выполнено сегодня!* Ты молодец! 🎉" if done else "⏳ Ещё не выполнено. Давай-давай!"

    await message.answer(
        f"🏋️ *День {day} — Сегодняшняя тренировка*\n\n"
        f"🦵 Приседания: *{w['squats']}* раз\n"
        f"💪 Пресс: *{w['abs']}* раз\n"
        f"🏋️ Планка: *{plank_str}*\n"
        f"🔥 Отжимания: *{w['pushups']}* раз\n\n"
        f"{status}",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )

@dp.message()
async def handle_message(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)

    text = message.text or ""

    # Быстрые кнопки тоже идут через Claude
    await bot.send_chat_action(message.chat.id, "typing")

    reply, mark_done, mark_missed = await ask_claude(user, text)

    if mark_done and not is_today_done(user):
        mark_today(user, done=True)
    elif mark_missed:
        mark_today(user, done=False)

    save_data(data)

    await message.answer(reply, reply_markup=main_keyboard())

# ── SCHEDULER: утреннее напоминание ──────────────────────────────────────────
async def send_morning_reminders():
    data = load_data()
    for user_id, user in data.items():
        try:
            day = get_day_number(user)
            w = get_workout(day)
            plank_str = f"{w['plank']}с"
            streak = calc_streak(user)

            streak_text = f"🔥 Серия уже {streak} дней!" if streak > 1 else "Начни свою серию сегодня!"

            await bot.send_message(
                int(user_id),
                f"☀️ *Доброе утро! Время тренироваться!*\n\n"
                f"📅 День *{day}* программы\n"
                f"{streak_text}\n\n"
                f"*Сегодняшняя тренировка:*\n"
                f"🦵 {w['squats']} приседаний\n"
                f"💪 {w['abs']} пресс\n"
                f"🏋️ {plank_str} планка\n"
                f"🔥 {w['pushups']} отжиманий\n\n"
                f"Отпишись когда сделаешь! 💪",
                parse_mode="Markdown",
                reply_markup=main_keyboard(),
            )
        except Exception as e:
            logging.warning(f"Can't send reminder to {user_id}: {e}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    # Каждый день в 8:00 по Вьетнаму (UTC+7)
    scheduler.add_job(send_morning_reminders, "cron", hour=REMINDER_HOUR, minute=0)
    scheduler.start()

    logging.info("FitBot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
