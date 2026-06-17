# AI Detection Backend API

Промежуточный API сервис для работы с Pangram API для обнаружения AI-генерированного текста в документах.

## Возможности

- 🔍 **Анализ файлов**: Поддержка PDF, DOCX, DOC, TXT файлов
- 📝 **Анализ текста**: Прямой анализ введенного текста
- 📚 **Пакетный анализ**: Анализ множественных текстов за один запрос
- 🗄️ **База данных**: Сохранение всех результатов анализа
- 🔄 **Автоматическое определение**: Выбор оптимального Pangram API endpoint
- 📊 **История и статистика**: Просмотр всех проведенных анализов
- 🌐 **Веб-интерфейс**: Удобный интерфейс для тестирования

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Запуск сервера

```bash
python app.py
```

Сервер будет доступен по адресу: http://localhost:5000

### 3. Тестирование

#### Веб-интерфейс
Откройте браузер и перейдите на http://localhost:5000

#### Командная строка
```bash
python test_api.py
```

## Использование API

### Загрузка и анализ файла

```bash
curl -X POST \
  http://localhost:5000/upload \
  -F 'file=@document.pdf'
```

### Анализ текста

```bash
curl -X POST \
  http://localhost:5000/analyze-text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Ваш текст для анализа..."
  }'
```

### Пакетный анализ

```bash
curl -X POST \
  http://localhost:5000/analyze-batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "Первый текст...",
      "Второй текст..."
    ]
  }'
```

## Архитектура

```
Frontend → Backend API → Pangram API
                   ↓
              SQLite Database
```

### Автоматическое определение Pangram endpoint

- **Standard API**: текст ≤ 400 слов
- **Sliding Window API**: текст > 400 слов  
- **Batch API**: множественные тексты

## Структура проекта

```
AiDetectionBackend/
├── app.py                 # Основное Flask приложение
├── requirements.txt       # Зависимости Python
├── test_api.py           # Тестовый скрипт
├── README.md             # Документация
├── API_DOCUMENTATION.md  # Подробная документация API
├── templates/
│   └── index.html        # Веб-интерфейс
├── uploads/              # Временные загруженные файлы
└── static/               # Статические файлы
```

## База данных

Используется PostgreSQL. Укажи строку подключения в `.env` переменной `DATABASE_URL`.

### Схема таблицы Detection:
- `id` - уникальный идентификатор
- `filename` - имя файла
- `file_type` - тип файла
- `text_length` - длина текста в словах
- `extracted_text` - извлеченный текст
- `api_endpoint` - использованный Pangram endpoint
- `ai_likelihood` - вероятность AI (0.0-1.0)
- `prediction` - текстовое предсказание
- `full_response` - полный ответ от Pangram
- `created_at` - время создания

## Поддерживаемые форматы файлов

- **PDF** (.pdf) - извлечение с помощью PyPDF2
- **Microsoft Word** (.docx, .doc) - извлечение с помощью python-docx
- **Текстовые файлы** (.txt) - с автоматическим определением кодировки

## Конфигурация

### Переменные окружения (опционально)

```bash
export PANGRAM_API_KEY="your-api-key-here"
export FLASK_ENV="development"
export DATABASE_URL="postgresql://postgres:password@localhost:5432/ai_detection"
export AI_MODE="pangram_plus_ai"
```

### Режимы AI (`AI_MODE`)

- `pangram_plus_ai` — Pangram API + локальная AI модель (скачивание/инициализация включены)
- `pangram_only` — только Pangram API (локальная модель и автообучение отключены)

### Основные настройки в app.py:

- `MAX_CONTENT_LENGTH`: 16MB (максимальный размер файла)
- `UPLOAD_FOLDER`: 'uploads' (папка для временных файлов)
- `PANGRAM_API_KEY`: API ключ для Pangram

## Безопасность

- ✅ Валидация типов файлов
- ✅ Ограничение размера файлов
- ✅ Очистка имен файлов
- ✅ Автоматическое удаление загруженных файлов
- ✅ CORS поддержка для фронтенда
- ✅ Обработка ошибок и исключений

## Мониторинг

### Получение статистики

```bash
curl http://localhost:5000/stats
```

### Просмотр истории

```bash
curl http://localhost:5000/history?page=1&per_page=10
```

## Разработка

### Логирование
API логирует все операции в консоль. Для продакшн использования рекомендуется настроить файловое логирование.

### Тестирование
Запустите тестовый скрипт для проверки всех endpoints:

```bash
python test_api.py
```

## Развертывание

### Локальное развертывание
```bash
python app.py
```

### Развертывание на сервере
1. Установите зависимости
2. Настройте обратный прокси (nginx)
3. Используйте WSGI сервер (gunicorn)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Поддержка

Для вопросов и проблем создайте issue в репозитории или обратитесь к документации Pangram API: https://pangram.readthedocs.io/

## Лицензия

Этот проект создан для интеграции с Pangram API. Убедитесь, что соблюдаете условия использования Pangram API. 