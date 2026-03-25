# 🔥 FitBot — Telegram бот для тренировок к лету

## Шаг 1 — Получи токены

### Telegram Bot Token:
1. Открой Telegram, найди @BotFather
2. Напиши `/newbot`
3. Придумай имя и username для бота
4. BotFather даст тебе токен вида: `1234567890:AAF...`

### Anthropic API Key:
1. Зайди на https://console.anthropic.com
2. Settings → API Keys → Create Key
3. Скопируй ключ вида: `sk-ant-...`

---

## Шаг 2 — Установка (на компьютере / сервере)

```bash
# Установи Python 3.10+, затем:
pip install -r requirements.txt
```

---

## Шаг 3 — Настройка

Открой `bot.py` и замени в начале файла:
```python
BOT_TOKEN = "ВСТАВЬ_ТОКЕН_СЮДА"          # токен от BotFather
ANTHROPIC_KEY = "ВСТАВЬ_ANTHROPIC_KEY"   # ключ от Anthropic
```

Или через переменные окружения (рекомендуется):
```bash
export BOT_TOKEN="твой_токен"
export ANTHROPIC_API_KEY="твой_ключ"
```

---

## Шаг 4 — Запуск

```bash
python bot.py
```

Бот запустится и начнёт слушать сообщения.
Каждое утро в **8:00 по Вьетнаму** будет приходить напоминание.

---

## Запуск 24/7 (чтобы бот работал постоянно)

### Вариант A — Railway.app (бесплатно, просто):
1. Зайди на https://railway.app
2. New Project → Deploy from GitHub (загрузи файлы)
3. Добавь переменные: `BOT_TOKEN` и `ANTHROPIC_API_KEY`
4. Deploy!

### Вариант B — VPS сервер (через screen):
```bash
screen -S fitbot
python bot.py
# Ctrl+A, затем D — бот работает в фоне
```

### Вариант C — systemd (Linux):
```ini
# /etc/systemd/system/fitbot.service
[Unit]
Description=FitBot

[Service]
WorkingDirectory=/path/to/fitbot
ExecStart=/usr/bin/python3 bot.py
Environment=BOT_TOKEN=твой_токен
Environment=ANTHROPIC_API_KEY=твой_ключ
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
systemctl enable fitbot && systemctl start fitbot
```

---

## Что умеет бот

- ☀️ Утренние напоминания в 8:00
- 💬 AI-чат через Claude (мотивация, ответы на вопросы)
- ✅ Отмечает тренировки выполненными
- 📊 Показывает статистику и серию дней
- 🏋️ Каждый день автоматически увеличивает нагрузку
