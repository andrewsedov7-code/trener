import asyncio
import json
import logging
import os
import random
from datetime import date, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_ТОКЕН")
REMINDER_HOUR = 8
DATA_FILE = "fitbot_data.json"
SUMMER = date(2026, 6, 1)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")

MOTIVATIONS = [
    "Ты огонь! Каждый день приближает тебя к лету мечты! 🔥",
    "Топ! Тело запомнит каждое усилие и отблагодарит на пляже! 💪",
    "Красавчик! Пока другие думают — ты делаешь! 😎",
    "Серия не прервана, прогресс идёт! Так держать! 🏆",
    "Лето будет твоим — это уже видно! ⚡",
    "Дисциплина — это и есть свобода! 🌟",
    "День за днём, кубик за кубиком! 🤖",
    "Многие бы пропустили — ты нет! Уважаю! 🙌",
    "Это не просто тренировка — это характер! 🎯",
    "Да ты монстр! Тело скажет спасибо через пару недель! 💥",
    "Июнь близко — ты будешь готов! ☀️",
    "Каждое приседание — шаг к лучшей версии себя! 💣",
    "Самое сложное — начать. Ты уже начал! 🧠",
    "Тело меняется — даже если не видно сразу! 🎉",
    "Скоро пляж — и ты там будешь выглядеть на все 100! 🌊",
]

DONE_PHRASES = [
    "Засчитано! ✅",
    "Отлично, молодец! ✅",
    "Зачёт! Ещё один день в копилку 💪",
    "День выполнен! Вот это результат ✅",
    "Горжусь тобой! 🔥",
    "Красавчик! День закрыт ✅",
]

MISSED_PHRASES = [
    "Бывает, не расстраивайся. Главное — завтра не пропускай! 💪",
    "Отдохнул — и снова в бой. Завтра с новыми силами! 🌅",
    "Пропуск зафиксирован. Но это не конец — завтра возвращайся!",
    "Один пропуск — не катастрофа. Два подряд — уже привычка. Завтра не подведи! 😉",
]

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
        data[uid] = {"start_date": date.today().isoformat(), "history": []}
        save_data(data)
    return data[uid]

def days_to_summer():
    return max(0, (SUMMER - date.today()).days)

def get_day_number(user):
    start = date.fromisoformat(user["start_date"])
    return max(1, (date.today() - start).days + 1)

def get_workout(day: int):
    # Старт: 30 присед, 30 пресс, 30 отжим, 30с планка
    # Каждый день: +1 к присед/пресс/отжим, +5с к планке
    d = day - 1
    return {
        "squats":  30 + d,
        "abs":     30 + d,
        "pushups": 10 + d,
        "plank":   30 + d * 5,
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
    for i in range(90):
        d = (today - timedelta(days=i)).isoformat()
        entry = next((h for h in user["history"] if h["date"] == d), None)
        if entry and entry["done"]:
            streak += 1
        elif i > 0:
            break
    return streak

def plank_fmt(seconds):
    m, s = divmod(seconds, 60)
    if m and s:
        return f"{m}м {s}с"
    elif m:
        return f"{m}м"
    return f"{s}с"

def workout_text(day):
    w = get_workout(day)
    return (
        f"Приседания: {w['squats']} раз\n"
        f"Пресс: {w['abs']} раз\n"
        f"Отжимания: {w['pushups']} раз\n"
        f"Планка: {plank_fmt(w['plank'])}"
    )

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Сделал!"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="⚡ Мотивируй!"), KeyboardButton(text="😔 Пропустил")],
            [KeyboardButton(text="🏋️ Тренировка на сегодня")],
        ],
        resize_keyboard=True,
    )

@dp.message(CommandStart())
async def cmd_start(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    day = get_day_number(user)
    left = days_to_summer()
    save_data(data)

    await message.answer(
        f"Привет! Я FitBot — твой тренер к лету! 🔥\n\n"
        f"До 1 июня: {left} дней\n"
        f"Сегодня день {day} программы\n\n"
        f"Тренировка на сегодня:\n"
        f"{workout_text(day)}\n\n"
        f"Каждый день: +1 повторение к каждому упражнению, +5с к планке\n\n"
        f"Напоминание каждое утро в 8:00! ☀️",
        reply_markup=main_keyboard(),
    )

@dp.message(F.text == "🏋️ Тренировка на сегодня")
async def cmd_today(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    day = get_day_number(user)
    done = is_today_done(user)
    left = days_to_summer()

    status = "Уже выполнено сегодня! Молодец!" if done else "Ещё не выполнено. Давай-давай! 💪"
    await message.answer(
        f"День {day} | До лета: {left} дней\n\n"
        f"{workout_text(day)}\n\n"
        f"{status}",
        reply_markup=main_keyboard(),
    )

@dp.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    day = get_day_number(user)
    streak = calc_streak(user)
    total = sum(1 for h in user["history"] if h["done"])
    left = days_to_summer()
    today_done = is_today_done(user)

    await message.answer(
        f"Статистика\n\n"
        f"До 1 июня: {left} дней\n"
        f"День программы: {day}\n"
        f"Серия: {streak} дней подряд 🔥\n"
        f"Всего тренировок: {total}\n"
        f"Сегодня: {'выполнено ✅' if today_done else 'не выполнено ⏳'}\n\n"
        f"Сегодняшняя тренировка:\n"
        f"{workout_text(day)}",
        reply_markup=main_keyboard(),
    )

@dp.message(F.text == "✅ Сделал!")
async def cmd_done(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)

    if is_today_done(user):
        await message.answer("Ты уже отметил тренировку сегодня! 😄 Одной хватит 💪", reply_markup=main_keyboard())
        return

    mark_today(user, done=True)
    streak = calc_streak(user)
    save_data(data)

    streak_text = f"\n\nСерия: {streak} дней подряд! 🔥" if streak > 1 else ""
    await message.answer(
        f"{random.choice(DONE_PHRASES)}\n\n{random.choice(MOTIVATIONS)}{streak_text}",
        reply_markup=main_keyboard(),
    )

@dp.message(F.text == "😔 Пропустил")
async def cmd_missed(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    mark_today(user, done=False)
    save_data(data)
    await message.answer(random.choice(MISSED_PHRASES), reply_markup=main_keyboard())

@dp.message(F.text == "⚡ Мотивируй!")
async def cmd_motivate(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    streak = calc_streak(user)
    day = get_day_number(user)
    left = days_to_summer()

    extra = ""
    if streak > 1:
        extra += f"\n\nУже {streak} дней подряд — не останавливайся! 🔥"
    if day > 7:
        extra += f"\nДень {day} позади — ты уже прошёл долгий путь!"
    extra += f"\nДо лета всего {left} дней — финишная прямая!"

    await message.answer(f"{random.choice(MOTIVATIONS)}{extra}", reply_markup=main_keyboard())

@dp.message()
async def handle_unknown(message: Message):
    text = (message.text or "").lower()
    data = load_data()
    user = get_user(data, message.from_user.id)

    done_kw = ["выполнил", "сделал", "готово", "done", "выполнено", "закончил"]
    missed_kw = ["пропустил", "не сделал", "не смог", "пропуск"]
    motiv_kw = ["мотив", "давай", "вперёд", "помоги"]

    if any(k in text for k in done_kw):
        if not is_today_done(user):
            mark_today(user, done=True)
            streak = calc_streak(user)
            save_data(data)
            streak_text = f"\n\nСерия: {streak} дней подряд! 🔥" if streak > 1 else ""
            await message.answer(
                f"{random.choice(DONE_PHRASES)}\n\n{random.choice(MOTIVATIONS)}{streak_text}",
                reply_markup=main_keyboard(),
            )
        else:
            await message.answer("Уже отмечено сегодня! 😄", reply_markup=main_keyboard())
    elif any(k in text for k in missed_kw):
        mark_today(user, done=False)
        save_data(data)
        await message.answer(random.choice(MISSED_PHRASES), reply_markup=main_keyboard())
    elif any(k in text for k in motiv_kw):
        await message.answer(random.choice(MOTIVATIONS), reply_markup=main_keyboard())
    else:
        await message.answer("Используй кнопки меню 👇 Или /start чтобы начать заново.", reply_markup=main_keyboard())

async def send_morning_reminders():
    data = load_data()
    left = days_to_summer()
    for user_id, user in data.items():
        try:
            day = get_day_number(user)
            streak = calc_streak(user)
            streak_text = f"Серия уже {streak} дней — не останавливайся! 🔥" if streak > 1 else "Начни свою серию сегодня! 💪"

            await bot.send_message(
                int(user_id),
                f"Доброе утро! Время тренироваться! ☀️\n\n"
                f"День {day} | До лета: {left} дней\n"
                f"{streak_text}\n\n"
                f"{workout_text(day)}\n\n"
                f"Отпишись когда сделаешь! 💪",
                reply_markup=main_keyboard(),
            )
        except Exception as e:
            logging.warning(f"Cant send to {user_id}: {e}")

async def main():
    scheduler.add_job(send_morning_reminders, "cron", hour=REMINDER_HOUR, minute=0)
    scheduler.start()
    logging.info("FitBot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
