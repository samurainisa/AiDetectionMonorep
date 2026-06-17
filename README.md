<div align="center">

# AI Detection

**Сервис детекции ИИ-сгенерированного текста и проверки на плагиат**

Flask · Vue 3 · PostgreSQL · Docker · Pangram API

</div>

---

## О проекте

Веб-приложение для анализа текстов и документов: определяет вероятность того,
что текст сгенерирован ИИ, и проверяет работу на плагиат по накопленному
корпусу. Поддерживает загрузку `pdf / docx / doc / txt`, историю проверок,
пользовательские аккаунты и экспорт отчётов в PDF.

### Возможности

- 🤖 **Детекция ИИ** — анализ через [Pangram API](https://www.pangram.com/) с расширенными статистическими признаками текста
- 🔍 **Антиплагиат** — сравнение с корпусом ранее загруженных документов
- 📄 **Форматы** — PDF, DOCX, DOC, TXT и анализ текста напрямую
- 👤 **Аккаунты** — JWT-авторизация, персональная история проверок
- 📊 **Аналитика** — статистика, фильтры, экспорт отчёта о плагиате в PDF

## Архитектура

```
                         ┌──────────────────────────────┐
   Браузер ──HTTPS──────▶│  Caddy (reverse proxy + TLS)  │
   ai-detection.ru       └───────────────┬──────────────┘
                             /            │  /api/*
                  ┌──────────▼─────┐  ┌───▼──────────────────┐
                  │   frontend     │  │      backend         │
                  │  Vue 3 + Vite  │  │  Flask + gunicorn    │
                  │  (nginx static)│  │  Pangram / антиплагиат│
                  └────────────────┘  └───────────┬──────────┘
                                          ┌────────▼────────┐
                                          │   PostgreSQL    │
                                          └─────────────────┘
```

Фронтенд и API живут на одном домене: статика отдаётся на `/`, запросы к API
проксируются на `/api/*`. Благодаря этому нет cross-origin запросов и не нужен
отдельный домен под бэкенд.

## Технологии

| Слой        | Стек                                                              |
|-------------|------------------------------------------------------------------|
| Frontend    | Vue 3, TypeScript, Vite, Pinia, Vue Router, PrimeVue, Tailwind    |
| Backend     | Python 3.11, Flask, SQLAlchemy, gunicorn, Pangram SDK, ReportLab  |
| База данных | PostgreSQL 16                                                     |
| Инфра       | Docker Compose, Caddy (авто-HTTPS через Let's Encrypt)            |

## Структура репозитория

```
.
├── AiDetectionFrontend/              # Vue 3 SPA (Vite, nginx Dockerfile)
├── AiDetectionKemsu/
│   └── AiDetectionBackend/           # Flask API (gunicorn Dockerfile)
│       ├── app.py                    # роуты и точка входа
│       ├── core/                     # БД, признаки, Pangram-клиент
│       ├── routes/                   # детектор, авторизация, отчёты
│       ├── plagiarism_engine.py      # движок антиплагиата
│       └── requirements.txt
├── docker-compose.yml                # локальная разработка (db + backend)
├── docker-compose.prod.yml           # продакшен (db + backend + frontend + caddy)
├── Caddyfile                         # reverse proxy + TLS для ai-detection.ru
├── DEPLOY.md                         # инструкция по деплою на VPS
└── .env.prod.example                 # шаблон переменных окружения
```

## Быстрый старт (локально)

### Backend + БД через Docker

```bash
cp .env.docker.example .env          # заполни PANGRAM_API_KEY и SECRET_KEY
docker compose up -d --build         # backend на http://localhost:5000
```

### Frontend (dev-сервер)

```bash
cd AiDetectionFrontend
npm install
npm run dev                          # http://localhost:5173
```

Dev-сборка обращается к API по адресу из `AiDetectionFrontend/.env.development`.

## Продакшен

Полная инструкция — в [DEPLOY.md](DEPLOY.md). Кратко:

```bash
cp .env.prod.example .env            # задать POSTGRES_PASSWORD, SECRET_KEY, PANGRAM_API_KEY
docker compose -f docker-compose.prod.yml up -d --build
```

Caddy сам выпустит TLS-сертификат для `ai-detection.ru` (нужны открытые
порты 80/443 и A-записи DNS на IP сервера).

## Переменные окружения

| Переменная            | Описание                                   | По умолчанию      |
|-----------------------|--------------------------------------------|-------------------|
| `SECRET_KEY`          | Секрет Flask (≥32 симв.)                    | — (обязательно)   |
| `POSTGRES_PASSWORD`   | Пароль PostgreSQL                          | — (обязательно)   |
| `PANGRAM_API_KEY`     | Ключ Pangram API                           | —                 |
| `AI_MODE`             | `pangram_only` \| `pangram_plus_ai`        | `pangram_only`    |
| `CORS_ORIGINS`        | Разрешённые origin'ы (через запятую)        | домены ai-detection|
| `CUDA_VISIBLE_DEVICES`| GPU (`-1` = выкл.)                          | `-1`              |

## Основные эндпоинты API

| Метод | Путь                          | Назначение                       |
|-------|-------------------------------|----------------------------------|
| POST  | `/analyze-text`               | Анализ текста напрямую           |
| POST  | `/upload`                     | Загрузка файла и анализ          |
| GET   | `/history`                    | История проверок (auth)          |
| GET   | `/stats`                      | Общая статистика                 |
| GET   | `/plagiarism/<id>`            | Отчёт о плагиате                  |
| GET   | `/plagiarism/<id>/pdf`        | Экспорт отчёта в PDF             |

## Лицензия

[MIT](LICENSE)
