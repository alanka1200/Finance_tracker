# 💰 Финансовый Трекер — Telegram Mini App

Полноценное мини-приложение для управления личными финансами в Telegram. **Бесплатно в продакшене**, с задумкой scale-up до сотен тысяч пользователей.

## ✨ Что внутри

- 📱 **Telegram Mini App** — красивый адаптивный интерфейс с анимациями
- 💸 **Учёт доходов и расходов** с категориями и тегами
- 🎯 **Финансовые цели** с прогресс-барами и пополнениями
- 📈 **Инвестиционный портфель** с расчётом прибыли/убытков
- 📊 **Аналитика** — тренды за 30 дней, разбивка по категориям, дашборд
- 🤖 **AI-советы** на базе Groq/Cerebras/Gemini (бесплатные API), с fallback на rule-based движок
- 🤝 **Реферальная программа** с уникальными кодами и share-ссылками
- 📤 **Экспорт** в CSV (для Excel) и JSON
- 🔒 **Безопасность**: HMAC-SHA256 валидация Telegram initData, JWT с refresh, soft delete, partial indexes
- 🌍 **Мультивалютность** (RUB, USD, EUR, BTC и т.д.)

---

## 📦 Архитектура

```
┌──────────────────────┐     HTTPS      ┌──────────────────────┐
│  Telegram Mini App   │ ─────────────> │  FastAPI backend     │
│  (GitHub Pages)      │ <───────────── │  (Render / Koyeb)    │
│  HTML/CSS/JS + Chart │  REST + JWT    │  + python-telegram-bot│
└──────────────────────┘                └──────────┬───────────┘
                                                   │
                                          asyncpg  │
                                                   ▼
                                         ┌─────────────────┐
                                         │ PostgreSQL      │
                                         │ (Neon Free)     │
                                         └─────────────────┘
```

**Backend:** Python 3.12 + FastAPI + python-telegram-bot 21 + SQLAlchemy 2.0 (async)
**Frontend:** Vanilla JS + Chart.js + Telegram WebApp SDK
**БД:** PostgreSQL 16 (через [Neon](https://neon.tech) — бесплатно, 0.5 GB, без сна)
**Хостинг бэка:** [Render Free](https://render.com) или [Koyeb Free](https://koyeb.com)
**Хостинг фронта:** GitHub Pages (статика, бесплатно навсегда)

---

## 🚀 Полный пошаговый деплой (с нуля до работающего бота)

> Время: ~30–45 минут. Без оплаты карты, без подписок.

### Шаг 1. Создаём бота в Telegram

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Отправь `/newbot`, придумай имя и username (должен заканчиваться на `bot`)
3. **Сохрани токен** — он выглядит как `1234567890:ABCdefGHI...`
4. Сразу настрой описание:
   - `/setdescription` — что делает бот
   - `/setabouttext` — короткое описание
   - `/setuserpic` — логотип

### Шаг 2. Получаем БД на Neon

1. Зарегистрируйся на [neon.tech](https://neon.tech) (через GitHub за 10 секунд)
2. Создай новый проект (регион — поближе к твоим юзерам, например Frankfurt)
3. На главной странице найди **Connection String** — скопируй
4. Преобразуй формат: замени `postgres://` на `postgresql+asyncpg://`
   ```
   # Было:
   postgres://user:pass@ep-xxx.eu-central-1.aws.neon.tech/finance
   # Стало:
   postgresql+asyncpg://user:pass@ep-xxx.eu-central-1.aws.neon.tech/finance
   ```

### Шаг 3. Получаем бесплатные ключи AI (опционально, но желательно)

Без этих ключей бот всё равно даёт советы — через rule-based движок. Но с LLM советы выходят живее.

- **Groq** (рекомендуется): [console.groq.com/keys](https://console.groq.com/keys) — 14 400 запросов/день, бесплатно
- **Cerebras** (запасной): [cloud.cerebras.ai](https://cloud.cerebras.ai) — 1 млн токенов/день
- **Gemini** (запасной): [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — 1 500 запросов/день

### Шаг 4. Заливаем код на GitHub

```bash
cd finance-tracker
git init
git add .
git commit -m "initial commit"
# Создай новый репозиторий на github.com (private или public)
git remote add origin https://github.com/<ваш_username>/finance-tracker.git
git branch -M main
git push -u origin main
```

### Шаг 5. Деплой backend на Render

1. Зарегистрируйся на [render.com](https://render.com) через GitHub
2. **New +** → **Blueprint** → выбери репо → Render найдёт `render.yaml` автоматически
3. В переменных окружения ВРУЧНУЮ задай:
   - `BOT_TOKEN` — из шага 1
   - `DATABASE_URL` — из шага 2
   - `GROQ_API_KEY` — из шага 3 (если есть)
   - `FRONTEND_URL` — пока поставь временный URL, обновим в шаге 6
   - `PUBLIC_URL` — будет вида `https://<service-name>.onrender.com`. Render покажет его на странице сервиса; вставь сюда.
   - `CORS_ORIGINS` — `https://<your_username>.github.io,https://web.telegram.org`
4. Render автоматически задеплоит через Docker. Подожди 5–10 минут (первая сборка медленная).
5. После деплоя зайди в логи и убедись, что видишь `✅ Webhook установлен`.

> **Важно:** Render free засыпает после 15 минут неактивности. Чтобы будить бот, можно настроить [UptimeRobot](https://uptimerobot.com) на пинг `/health` каждые 5 минут — бесплатно.

### Шаг 6. Деплой фронтенда на GitHub Pages

1. В настройках репозитория на GitHub → **Pages** → **Source: Deploy from a branch**
2. Branch: `main`, Folder: `/frontend`
3. Жди пару минут — GitHub скажет URL вида `https://<your_username>.github.io/finance-tracker/`
4. Тебе нужно сообщить фронтенду адрес backend'а. Открой `frontend/index.html` локально и **перед тегом `<script src="api.js">`** добавь:
   ```html
   <script>window.API_BASE_URL = 'https://your-backend.onrender.com';</script>
   ```
5. Закоммить и запушь. GitHub Pages обновится автоматически за минуту.
6. **Вернись в Render** и обнови переменную `FRONTEND_URL` на полученный адрес GitHub Pages, перезапусти сервис.

### Шаг 7. Подключаем Mini App к боту

В [@BotFather](https://t.me/BotFather):

1. `/setmenubutton` → выбери своего бота → пришли URL фронта (`https://<user>.github.io/finance-tracker/`) → текст кнопки `📱 Открыть приложение`
2. `/setdomain` → выбери бота → пришли `https://<your_username>.github.io` (без пути)

Готово! Открой бота в Telegram, отправь `/start` — должна появиться кнопка для запуска Mini App.

---

## 🛠 Локальная разработка

```bash
# 1. Клонируй и подготовь окружение
git clone https://github.com/<your_username>/finance-tracker.git
cd finance-tracker
cp .env.example .env

# 2. Заполни .env (минимум: BOT_TOKEN, DATABASE_URL, JWT_SECRET, WEBHOOK_SECRET)
#    Сгенерировать секреты:
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Поднимаем стек через Docker
docker compose up

# Backend будет на http://localhost:8080/docs (Swagger UI)
```

Для разработки фронта просто открой `frontend/index.html` в браузере. Telegram WebApp возможностей в обычном браузере не будет, но базовый UI можно проверить.

### Запуск тестов

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## 📁 Структура проекта

```
finance-tracker/
├── app/                       # Backend Python код
│   ├── main.py               # FastAPI + lifespan + webhook регистрация
│   ├── config.py             # Pydantic Settings из .env
│   ├── deps.py               # FastAPI dependencies (current_user, db)
│   ├── core/                 # logging, security (JWT)
│   ├── db/                   # async SQLAlchemy движок
│   ├── models/               # ORM модели (User, Transaction, Goal, ...)
│   ├── schemas/              # Pydantic схемы для API
│   ├── services/             # бизнес-логика (auth, transactions, advice, ...)
│   ├── api/                  # HTTP роутеры
│   │   ├── telegram.py       # webhook endpoint
│   │   └── v1/               # REST API (/api/v1/...)
│   └── bot/                  # Telegram bot handlers
├── migrations/                # Alembic миграции
├── frontend/                  # Telegram Mini App (статика)
│   ├── index.html
│   ├── styles.css
│   ├── api.js                # клиент к backend
│   ├── ui.js                 # UI helpers (модалки, форматтеры)
│   └── app.js                # bootstrap, рендеринг, события
├── tests/                     # pytest тесты
├── Dockerfile
├── docker-compose.yml
├── render.yaml                # Render Blueprint config
├── requirements.txt
└── .env.example
```

---

## 🔐 Безопасность

- **HMAC-SHA256 проверка** Telegram initData (защита от подмены пользователя)
- **Constant-time сравнение** хешей (защита от timing-атак)
- **JWT с разделением access/refresh** (короткий access — 60 мин, refresh — 30 дней)
- **TTL для initData** (24 часа по умолчанию)
- **Webhook secret** двойной защиты: путь + заголовок
- **Soft delete** + partial indexes по `deleted_at`
- **Non-root** Docker user
- **CORS whitelist**
- **Pinned versions** во всех зависимостях

---

## 💰 Стоимость в продакшене

| Ресурс | Сервис | Лимит free | На сколько хватит |
|--------|--------|------------|------------------|
| Backend | Render Free | 750ч/месяц | Один сервис на всю активность 24/7 |
| БД | Neon Free | 0.5 GB | ~50 000 транзакций |
| Frontend | GitHub Pages | 100 GB трафика/мес | На годы вперёд |
| AI Groq | бесплатно | 14 400 RPD | На несколько сотен активных юзеров |
| **ИТОГО** | | | **0 ₽/месяц до ~1000 пользователей** |

---

## 🎯 Roadmap (что добавить дальше)

- [ ] Конвертация валют через [exchangerate.host](https://exchangerate.host)
- [ ] Подтягивание текущих цен акций (Finnhub) и крипты (CoinGecko)
- [ ] Уведомления о превышении бюджета (Telegram-сообщения раз в день/неделю)
- [ ] Распознавание чеков через OCR (Tesseract / OCR.space free)
- [ ] Полнотекстовый поиск по транзакциям (PostgreSQL trgm)
- [ ] Графики целей с прогнозом достижения
- [ ] Семейные кошельки (несколько юзеров на один аккаунт)
- [ ] Дашборд для админов

---

## 📞 Поддержка

Если что-то сломалось:
1. Проверь логи в Render → Logs
2. Проверь `/health` твоего бэка — должен возвращать `{"status":"ok"}`
3. Проверь, что webhook зарегистрировался: `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

---

## 📜 Лицензия

MIT — делай с этим что хочешь. Если приложение поможет тебе или твоим пользователям — это уже круто. ❤️
