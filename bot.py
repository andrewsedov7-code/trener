import asyncio
import json
import logging
import os
import random
from datetime import date, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_ТОКЕН_СЮДА")
REMINDER_HOUR = 8
DATA_FILE = "fitbot_data.json"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")

# ── МОТИВАШКИ ─────────────────────────────────────────────────────────────────
MOTIVATIONS = [
    "Ты огонь! Каждый день приближает тебя к лету мечты!",
    "Топ результат! Тело запомнит каждое усилие — и отблагодарит на пляже!",
    "Красавчик! Пока другие думают — ты делаешь!",
    "Вот это я понимаю! Серия не прервана, прогресс идёт!",
    "Зачёт! Лето будет твоим — это уже видно!",
    "Так держать! Дисциплина — это и есть свобода!",
    "Машина! День за днём, кубик за кубиком!",
    "Уважаю! Многие бы пропустили — ты нет!",
    "Горжусь тобой! Это не просто тренировка — это характер!",
    "Легенда! Продолжай в том же духе!",
    "Да ты монстр! Тело скажет спасибо уже через пару недель!",
    "Правильно делаешь! Июнь близко — ты будешь готов!",
    "Бомба! Каждое приседание — это шаг к лучшей версии себя!",
    "Сильный духом! Самое сложное — начать. Ты уже начал!",
    "Отличная работа! Тело меняется — даже если не видно сразу!",
    "Неостановим! Ещё один день — ещё один шаг к форме!",
    "Жара! Скоро пляж — и ты там будешь выглядеть на все 100!",
    "Зверь! Уже чувствуешь как становишься сильнее?",
    "Топ! Каждый день — это маленькая победа над собой!",
    "Красота! Тело — это проект, и ты сейчас строишь шедевр!",
]

DONE_PHRASES = [
    "Засчитано! ✅",
    "Отлично, молодец! ✅",
    "Зачёт! Ещё один день в копилку 💪",
    "Вот это результат! День выполнен ✅",
    "Так держать! Горжусь тобой 🔥",
    "Красавчик! День закрыт ✅",
    "Огонь! Так и продолжай 🔥",
]

MISSED_PHRASES = [
    "Бывает, не расстраивайся. Главное — завтра не пропускай! Серия начнётся заново 💪",
    "Ничего страшного! Отдохнул — и снова в бой. Завтра с новыми силами! 🌅",
    "Пропуск зафиксирован. Но это не конец! Завтра возвращайся — серия пойдёт снова!",
    "Ок, записал. Помни: один пропуск — не катастрофа. Два подряд — уже привычка. Завтра не подведи!",
]

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
        "squats":  70 + d,
        "abs":     70 + d,
        "plank":   70 + d * 5,
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
    for i in range(90):
        d = (today - timedelta(days=i)).isoformat()
        entry = next((h for h in user["history"] if h["date"] == d), None)
        if entry and entry["done"]:
            streak += 1
        elif i > 0:
            break
    return streak

def plank_fmt(seconds):
    m = seconds // 60
    s = seconds % 60
    if m and s:
        return f"{m}м {s}с"
    elif m:
        return f"{m}м"
    return f"{s}с"

def get_stats_text(user):
    day = get_day_number(user)
    w = get_workout(day)
    streak = calc_streak(user)
    total = sum(1 for h in user["history"] if h["done"])
    today_done = is_today_done(user)

    return (
        f"Статистика\n\n"
        f"День программы: {day}\n"
        f"Серия: {streak} дней подряд\n"
        f"Всего тренировок: {total}\n"
        f"{'Сегодня выполнено!' if today_done else 'Сегодня ещё не выполнено'}\n\n"
        f"Сегодняшняя тренировка:\n"
        f"Приседания: {w['squats']} раз\n"
        f"Пресс: {w['abs']} раз\n"
        f"Планка: {plank_fmt(w['plank'])}\n"
        f"Отжимания: {w['pushups']} раз"
    )

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

    await message.answer(
        f"Привет! Я FitBot — твой тренер к лету!\n\n"
        f"Сегодня день {day} программы.\n\n"
        f"Твоя тренировка:\n"
        f"Приседания: {w['squats']} раз\n"
        f"Пресс: {w['abs']} раз\n"
        f"Планка: {plank_fmt(w['plank'])}\n"
        f"Отжимания: {w['pushups']} раз\n\n"
        f"Каждый день: +1 приседание, +1 пресс, +1 отжимание, +5с планка\n"
        f"Напоминание каждое утро в 8:00!\n\n"
        f"Вперёд к лету! 🌞",
        reply_markup=main_keyboard(),
    )

@dp.message(Command("stats"))
@dp.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    await message.answer(get_stats_text(user), reply_markup=main_keyboard())

@dp.message(F.text == "🏋️ Сегодняшняя тренировка")
async def cmd_today(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    day = get_day_number(user)
    w = get_workout(day)
    done = is_today_done(user)
    status = "Уже выполнено сегодня! Ты молодец!" if done else "Ещё не выполнено. Давай-давай!"

    await message.answer(
        f"День {day} — Сегодняшняя тренировка\n\n"
        f"Приседания: {w['squats']} раз\n"
        f"Пресс: {w['abs']} раз\n"
        f"Планка: {plank_fmt(w['plank'])}\n"
        f"Отжимания: {w['pushups']} раз\n\n"
        f"{status}",
        reply_markup=main_keyboard(),
    )

@dp.message(F.text == "✅ Тренировка выполнена!")
async def cmd_done(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)

    if is_today_done(user):
        await message.answer("Ты уже отметил тренировку сегодня! Не жадничай — одной хватит 💪", reply_markup=main_keyboard())
        return

    mark_today(user, done=True)
    streak = calc_streak(user)
    save_data(data)

    streak_text = f"\n\nСерия: {streak} дней подряд! Не останавливайся!" if streak > 1 else ""
    await message.answer(
        f"{random.choice(DONE_PHRASES)}\n\n{random.choice(MOTIVATIONS)}{streak_text}",
        reply_markup=main_keyboard(),
    )

@dp.message(F.text == "😔 Пропустил сегодня")
async def cmd_missed(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    mark_today(user, done=False)
    save_data(data)
    await message.answer(random.choice(MISSED_PHRASES), reply_markup=main_keyboard())

@dp.message(F.text == "⚡ Мотивируй меня!")
async def cmd_motivate(message: Message):
    data = load_data()
    user = get_user(data, message.from_user.id)
    streak = calc_streak(user)
    day = get_day_number(user)

    streak_text = f"\n\nУже {streak} дней подряд — не останавливайся!" if streak > 1 else ""
    day_text = f"\nДень {day} — ты уже прошёл долгий путь!" if day > 5 else ""

    await message.answer(
        f"{random.choice(MOTIVATIONS)}{streak_text}{day_text}",
        reply_markup=main_keyboard(),
    )

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
            streak_text = f"\n\nСерия: {streak} дней подряд!" if streak > 1 else ""
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
        await message.answer("Используй кнопки меню 👇 Или напиши /start", reply_markup=main_keyboard())

# ── SCHEDULER ─────────────────────────────────────────────────────────────────
async def send_morning_reminders():
    data = load_data()
    for user_id, user in data.items():
        try:
            day = get_day_number(user)
            w = get_workout(day)
            streak = calc_streak(user)
            streak_text = f"Серия уже {streak} дней — не останавливайся!" if streak > 1 else "Начни свою серию сегодня!"

            await bot.send_message(
                int(user_id),
                f"Доброе утро! Время тренироваться! ☀️\n\n"
                f"День {day} программы\n"
                f"{streak_text}\n\n"
                f"Сегодняшняя тренировка:\n"
                f"Приседания: {w['squats']} раз\n"
                f"Пресс: {w['abs']} раз\n"
                f"Планка: {plank_fmt(w['plank'])}\n"
                f"Отжимания: {w['pushups']} раз\n\n"
                f"Отпишись когда сделаешь! 💪",
                reply_markup=main_keyboard(),
            )
        except Exception as e:
            logging.warning(f"Can't send reminder to {user_id}: {e}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    scheduler.add_job(send_morning_reminders, "cron", hour=REMINDER_HOUR, minute=0)
    scheduler.start()
    logging.info("FitBot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
