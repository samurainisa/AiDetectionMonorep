# Деплой AI Detection на VPS (docker-compose + Caddy)

Архитектура: один сервер, всё в Docker. Caddy терминирует HTTPS для
`ai-detection.ru`, отдаёт фронтенд на `/` и проксирует API на `/api/*` →
бэкенд. Отдельный домен для бэкенда не нужен, CORS не задействован
(всё в одном origin).

```
Браузер ──HTTPS──> Caddy ─┬─ /api/* ─> backend (gunicorn:5000)
   ai-detection.ru        └─ /      ─> frontend (nginx, статика Vue)
                                        backend ──> db (postgres)
```

## 1. Подготовка домена (reg.ru)

В панели reg.ru у домена `ai-detection.ru` добавь A-записи на IP сервера:

| Тип | Имя  | Значение         |
|-----|------|------------------|
| A   | @    | `<IP_сервера>`   |
| A   | www  | `<IP_сервера>`   |

DNS-серверы оставь `ns1.reg.ru` / `ns2.reg.ru`. Подожди распространения
(обычно 15–60 мин). Проверка: `nslookup ai-detection.ru`.

## 2. Сервер: Docker

Ubuntu/Debian:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # перелогиниться после этого
```

Открой порты 80 и 443 (firewall/облако): они нужны Caddy для выпуска
Let's Encrypt сертификата.

## 3. Код и переменные окружения

```bash
# Скопируй проект на сервер (git clone / scp), затем:
cd AiDetectionKemsuMonorep
cp .env.prod.example .env
nano .env
```

Обязательно задай в `.env`:
- `POSTGRES_PASSWORD` — надёжный пароль БД;
- `SECRET_KEY` — сгенерируй: `openssl rand -hex 32`;
- `PANGRAM_API_KEY` — ключ Pangram (уже подставлен пример).

> `.env` не коммить в git — там секреты.

## 4. Запуск

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Проверка статуса и логов:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f caddy     # выпуск сертификата
docker compose -f docker-compose.prod.yml logs -f backend
```

Открой `https://ai-detection.ru` — должен загрузиться интерфейс.
API доступен на `https://ai-detection.ru/api/` (например `/api/stats`).

## 5. Обновление после изменений в коде

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## 6. Полезное

- Бэкап БД:
  `docker compose -f docker-compose.prod.yml exec db pg_dump -U postgres ai_detection > backup.sql`
- Остановить: `docker compose -f docker-compose.prod.yml down`
  (данные БД, загрузки и сертификаты сохраняются в volumes).
- Полная очистка с БД: `docker compose -f docker-compose.prod.yml down -v` (⚠️ удалит данные).

## Замечания

- Загрузки храним в volume `backend_uploads` (файлы анализа удаляются
  после обработки, volume нужен для временных файлов).
- Таблицы БД создаются автоматически при старте бэкенда (`wsgi.py` →
  `init_database`).
- Тяжёлые train-зависимости в образ не ставятся (`INSTALL_TRAINING_DEPS=false`).
- Локальная разработка по-прежнему использует `docker-compose.yml`.
