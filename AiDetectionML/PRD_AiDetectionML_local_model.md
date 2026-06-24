# PRD: Доработка ML-части проекта AiDetectionML

## 1. Название

**AiDetectionML: локальный ML-модуль детекции AI-текста с обучаемой моделью, весами и Docker-развёртыванием**

## 2. Контекст

В проекте уже есть папка `AiDetectionML` с подготовленными файлами датасета:

```text
AiDetectionML/
  train.jsonl
  valid.jsonl
  test.jsonl
```

Датасет: **LLMTrace Classification Dataset**.

Формат одной строки JSONL:

```json
{
  "lang": "ru",
  "label": "ai",
  "model": "gemini-2.0-flash",
  "data_type": "news",
  "prompt_type": "delete",
  "topic_id": "739704ad37cfe92408aa7856a7f13696",
  "text": "Текст для классификации...",
  "prompt": "Промпт, использованный для генерации..."
}
```

Целевая задача: бинарная классификация текста.

```text
human → 0
ai    → 1
```

## 3. Главная цель доработки

Реализовать локальный ML-контур, который:

1. обучает компактную модель на имеющихся JSONL-файлах;
2. сохраняет веса модели локально;
3. считает метрики на `valid.jsonl` и `test.jsonl`;
4. запускает отдельный ML API-сервис;
5. работает в Docker;
6. может быть подключён к основному backend проекта.

Главная защита доработки:

> В проекте реализован не только внешний аналитический модуль, но и пилотный локальный классификатор с собственными весами, метриками и API. Это подтверждает возможность перехода к локальному ML-контуру.

## 4. Что НЕ является целью

За один день не требуется:

1. достичь промышленной точности;
2. обучить тяжёлую DeBERTa/BERT-base модель;
3. реализовать LIME/SHAP;
4. реализовать полноценную character-level детекцию;
5. обучать модель на всех языках и всех доменах сразу;
6. делать нагрузочное тестирование;
7. подключать LMS.

## 5. Рекомендуемая стратегия

### Основной путь

Использовать `cointegrated/rubert-tiny2` как базовую модель и дообучить её через `AutoModelForSequenceClassification`.

Причины:

1. модель небольшая;
2. ориентирована на русский язык;
3. подходит для классификации;
4. сохраняется через `save_pretrained()`;
5. после обучения появляются нормальные артефакты модели: конфиг, tokenizer, веса;
6. удобно завернуть в Docker.

### Фолбэк, если fine-tuning не взлетит

Если обучение transformer-классификатора окажется слишком тяжёлым:

1. использовать `cointegrated/rubert-tiny2` как frozen encoder;
2. получить embeddings;
3. обучить `LogisticRegression`;
4. сохранить `classifier.joblib`.

Но для защиты лучше успеть основной путь, потому что он даёт полноценную папку модели с весами.

## 6. Язык и объём данных

Для первой версии использовать только русский язык:

```text
lang == "ru"
```

Причины:

1. тема ВКР связана с российским образовательным контекстом;
2. модель `rubert-tiny2` ориентирована на русский язык;
3. обучение будет быстрее;
4. проще объяснять результат комиссии.

Английский язык оставить как дальнейшее развитие.

## 7. Балансировка данных

Перед обучением нужно проверить распределение:

1. по `label`;
2. по `lang`;
3. по `data_type`;
4. по длине текста.

Для MVP достаточно:

1. взять только `lang == "ru"`;
2. сбалансировать классы `human` и `ai`;
3. при необходимости ограничить выборку для быстрого обучения.

Рекомендуемые размеры для быстрого прогона:

```text
train: до 3000 human + 3000 ai
valid: до 500 human + 500 ai
test: до 500 human + 500 ai
```

Если ресурсов совсем мало:

```text
train: 1000 human + 1000 ai
valid: 200 human + 200 ai
test: 200 human + 200 ai
```

## 8. Структура проекта после доработки

```text
AiDetectionML/
  train.jsonl
  valid.jsonl
  test.jsonl

  README.md
  requirements.txt

  configs/
    train_config.yaml

  data/
    processed/
      train_ru.jsonl
      valid_ru.jsonl
      test_ru.jsonl
      dataset_stats.json

  scripts/
    01_inspect_dataset.py
    02_prepare_dataset.py
    03_train_model.py
    04_evaluate_model.py
    05_predict_text.py

  ml_service/
    app.py
    Dockerfile
    requirements.txt
    src/
      predictor.py
      schemas.py
      preprocess.py

  models/
    rubert_tiny2_ai_detector/
      config.json
      model.safetensors или pytorch_model.bin
      tokenizer_config.json
      special_tokens_map.json
      vocab.txt / tokenizer files
      training_args.json
      metrics.json
      label_map.json
      confusion_matrix.png

  artifacts/
    reports/
      dataset_report.md
      training_report.md
```

## 9. Функциональные требования

### FR-1. Анализ датасета

Скрипт: `scripts/01_inspect_dataset.py`.

Должен:

1. прочитать `train.jsonl`, `valid.jsonl`, `test.jsonl`;
2. посчитать количество строк;
3. посчитать распределение по `label`;
4. посчитать распределение по `lang`;
5. посчитать распределение по `data_type`;
6. посчитать среднюю/медианную длину текста;
7. сохранить отчёт в `data/processed/dataset_stats.json`;
8. сохранить markdown-отчёт в `artifacts/reports/dataset_report.md`.

### FR-2. Подготовка данных

Скрипт: `scripts/02_prepare_dataset.py`.

Должен:

1. отфильтровать `lang == "ru"`;
2. удалить строки без `text`;
3. удалить слишком короткие тексты;
4. удалить дубликаты по `text`;
5. сбалансировать классы `human` и `ai`;
6. сохранить `data/processed/train_ru.jsonl`, `valid_ru.jsonl`, `test_ru.jsonl`.

Преобразование label:

```python
{"human": 0, "ai": 1}
```

### FR-3. Обучение модели

Скрипт: `scripts/03_train_model.py`.

Должен:

1. загрузить `cointegrated/rubert-tiny2`;
2. создать `AutoModelForSequenceClassification` с `num_labels=2`;
3. обучить модель на `train_ru.jsonl`;
4. валидироваться на `valid_ru.jsonl`;
5. сохранить модель в `models/rubert_tiny2_ai_detector/`.

Минимальные параметры обучения:

```yaml
model_name: cointegrated/rubert-tiny2
max_length: 512
num_train_epochs: 1
per_device_train_batch_size: 8
per_device_eval_batch_size: 8
learning_rate: 0.00002
weight_decay: 0.01
```

Если CPU и очень медленно:

```yaml
max_length: 256
num_train_epochs: 1
per_device_train_batch_size: 4
```

### FR-4. Оценка качества

Скрипт: `scripts/04_evaluate_model.py`.

Должен считать:

1. Accuracy;
2. Precision;
3. Recall;
4. F1-score;
5. confusion matrix;
6. количество объектов в test;
7. распределение классов.

Результаты сохранить:

```text
models/rubert_tiny2_ai_detector/metrics.json
models/rubert_tiny2_ai_detector/confusion_matrix.png
artifacts/reports/training_report.md
```

### FR-5. Локальный predict

Скрипт: `scripts/05_predict_text.py`.

Пример ответа:

```json
{
  "label": "ai",
  "ai_probability": 0.73,
  "human_probability": 0.27,
  "confidence": "medium_ai",
  "model": "rubert_tiny2_ai_detector",
  "mode": "local"
}
```

### FR-6. ML API

Сервис: `ml_service/app.py`. Фреймворк: FastAPI.

Endpoints:

```text
GET /health
GET /model-info
POST /predict
```

## 10. Логика confidence

```text
ai_probability >= 0.80 → high_ai
0.60 <= ai_probability < 0.80 → medium_ai
0.40 <= ai_probability < 0.60 → uncertain
0.20 <= ai_probability < 0.40 → medium_human
ai_probability < 0.20 → high_human
```

В интерфейсе нельзя писать «нарушение доказано». Правильная формулировка:

```text
Обнаружены признаки генеративного происхождения текста. Рекомендуется дополнительная проверка преподавателем.
```

## 11. Docker

### ML Dockerfile

Файл: `ml_service/Dockerfile`.

Требования:

1. Python 3.11 slim;
2. установка зависимостей;
3. копирование `ml_service`;
4. копирование `models`;
5. запуск через uvicorn.

Команда запуска:

```bash
uvicorn app:app --host 0.0.0.0 --port 8001
```

### docker-compose

В будущем добавить сервис:

```yaml
ml_service:
  build:
    context: ./AiDetectionML
    dockerfile: ml_service/Dockerfile
  ports:
    - "8001:8001"
  environment:
    - MODEL_PATH=/app/models/rubert_tiny2_ai_detector
    - DEVICE=cpu
```

## 12. Переменные окружения

```env
MODEL_PATH=/app/models/rubert_tiny2_ai_detector
DEVICE=cpu
MAX_TEXT_LENGTH=12000
ML_SERVICE_PORT=8001
```

Для backend:

```env
AI_MODE=local_student
ML_SERVICE_URL=http://ml_service:8001/predict
```

## 13. Интеграция с backend

Backend должен поддерживать режим `AI_MODE=local_student`.

В этом режиме backend:

1. принимает документ;
2. извлекает текст;
3. очищает текст;
4. отправляет текст в `ML_SERVICE_URL`;
5. получает probability;
6. сохраняет результат;
7. показывает отчёт.

## 14. Предобработка текста

Функция `preprocess_text(text: str) -> str` должна:

1. приводить текст к строке;
2. удалять лишние пробелы;
3. удалять пустые строки;
4. ограничивать длину;
5. возвращать очищенный текст.

Не нужно агрессивно удалять пунктуацию и не нужно lower-case весь текст. Для BERT-подобных моделей это может ухудшить качество.

## 15. Работа с длинными документами

Для MVP можно ограничить текст:

```text
MAX_TEXT_LENGTH=12000 символов
```

Для следующей версии реализовать chunking:

```text
chunk_size = 2500 символов
overlap = 300 символов
document_score = среднее top-3 самых высоких chunk scores
```

## 16. Нефункциональные требования

### Производительность

MVP должен работать на CPU.

Целевой результат:

```text
1 текст до 12000 символов → до 3–10 секунд на CPU
```

### Воспроизводимость

Должны фиксироваться:

1. random seed;
2. версия модели;
3. параметры обучения;
4. дата обучения;
5. размер датасета;
6. метрики.

### Безопасность

1. не логировать полный текст документа;
2. логировать только длину текста, label, probability, model_version;
3. не хранить персональные данные в ML-сервисе;
4. ML-сервис должен быть stateless.

## 17. Acceptance Criteria

Доработка считается выполненной, если:

1. `train.jsonl`, `valid.jsonl`, `test.jsonl` читаются скриптами;
2. есть отчёт по датасету;
3. есть подготовленные русскоязычные split-файлы;
4. модель обучается без ручных правок;
5. модель сохраняется в `models/rubert_tiny2_ai_detector`;
6. есть `metrics.json`;
7. есть `confusion_matrix.png`;
8. работает `scripts/05_predict_text.py`;
9. работает FastAPI endpoint `/predict`;
10. ML-сервис собирается в Docker;
11. есть README с командами запуска;
12. backend может быть переключён в режим `AI_MODE=local_student`.

## 18. Definition of Done

Готовая доработка должна позволять показать на защите:

1. где лежат данные;
2. как данные подготовлены;
3. где код обучения;
4. где лежат веса модели;
5. какие метрики получены;
6. как модель запускается локально;
7. как backend обращается к ML-сервису;
8. как результат отображается в отчёте.

## 19. Команды, которые должны работать

```bash
cd AiDetectionML

python scripts/01_inspect_dataset.py
python scripts/02_prepare_dataset.py
python scripts/03_train_model.py
python scripts/04_evaluate_model.py
python scripts/05_predict_text.py --text "Текст для проверки"

cd ml_service
uvicorn app:app --host 0.0.0.0 --port 8001
```

Docker:

```bash
cd AiDetectionML
docker build -f ml_service/Dockerfile -t ai-detection-ml .
docker run -p 8001:8001 ai-detection-ml
```

## 20. Что говорить на защите

### Вопрос: вы обучили свою модель?

```text
В рамках доработки был реализован пилотный локальный классификатор на базе лёгкой BERT-архитектуры. Модель обучалась на подготовленном датасете LLMTrace, включающем русскоязычные тексты классов human и ai. Это не промышленная модель, но рабочий локальный ML-прототип с сохранёнными весами, метриками и API.
```

### Вопрос: где модель?

```text
Модель сохранена локально в папке models/rubert_tiny2_ai_detector. Там находятся веса, конфигурация, tokenizer и файл метрик. Сервис может запускаться локально и в Docker.
```

### Вопрос: какие данные использовали?

```text
Использовали LLMTrace Classification Dataset. Это bilingual English/Russian датасет для бинарной классификации human vs ai. Для первой версии мы взяли русскоязычную часть, чтобы соответствовать образовательному контексту работы и снизить требования к ресурсам.
```

### Вопрос: почему модель маленькая?

```text
Мы сознательно выбрали компактную модель, потому что задача стояла не обучить тяжёлую промышленную DeBERTa, а реализовать воспроизводимый локальный ML-контур на ограниченных ресурсах. Для ВКР важна проверка архитектурной возможности: данные → обучение → веса → API → Docker.
```

### Вопрос: можно ли по результату модели наказывать студента?

```text
Нет. Результат модели — вероятностный сигнал для преподавателя. Он показывает, что работа может требовать дополнительной проверки, но не является доказательством нарушения.
```

## 21. План на 1 день

### 1–2 часа

1. создать структуру папок;
2. написать `requirements.txt`;
3. написать `01_inspect_dataset.py`;
4. проверить JSONL-файлы.

### 2–3 часа

1. написать `02_prepare_dataset.py`;
2. отфильтровать русский язык;
3. сбалансировать классы;
4. сохранить processed-файлы.

### 3–5 часов

1. написать `03_train_model.py`;
2. запустить обучение;
3. сохранить модель.

### 1 час

1. написать `04_evaluate_model.py`;
2. сохранить `metrics.json`;
3. сохранить confusion matrix.

### 1–2 часа

1. написать `ml_service/app.py`;
2. проверить `/predict`;
3. написать Dockerfile.

### 30 минут

1. оформить README;
2. сделать скриншоты;
3. подготовить формулировки для защиты.

## 22. Риски

### Риск: обучение слишком долгое

Решение:

1. уменьшить `max_length` до 256;
2. уменьшить train size;
3. поставить `num_train_epochs=1`;
4. использовать batch size 4.

### Риск: метрики плохие

Решение:

1. честно назвать модель пилотной;
2. показать, что есть локальный ML-контур;
3. добавить это в дальнейшее развитие.

### Риск: ошибка с форматами JSONL

Решение:

1. в скриптах делать валидацию полей;
2. пропускать битые строки;
3. логировать количество пропусков.

## 23. Итоговая формула доработки

```text
LLMTrace JSONL → фильтрация ru → балансировка human/ai → fine-tuning rubert-tiny2 → сохранение весов → метрики → FastAPI ML service → Docker → подключение к backend
```

## 24. Главное требование

Не делать вид, что модель промышленная. Формулировка:

```text
Реализован пилотный локальный ML-модуль, подтверждающий возможность перехода от внешнего аналитического компонента к локальной модели.
```
