# AiDetectionML

Пилотный локальный ML-контур для бинарной классификации текста:

```text
human -> 0
ai -> 1
```

Базовая модель: `cointegrated/rubert-tiny2`.

Это proof-of-concept для ВКР, а не промышленная система. Результат вероятностный и не должен использоваться как доказательство нарушения или основание для наказания студента.

## Установка

```bash
pip install -r requirements.txt
```

## Pipeline

Команды запускаются из корня `AiDetectionML`.

```bash
python scripts/01_inspect_dataset.py
python scripts/02_prepare_dataset.py
python scripts/03_train_model.py
python scripts/04_evaluate_model.py
python scripts/05_predict_text.py --text "Текст для проверки"
```

Для быстрого запуска на слабой машине можно уменьшить значения в `configs/train_config.yaml`:

```yaml
max_train_per_class: 1000
max_valid_per_class: 200
max_test_per_class: 200
max_length: 256
per_device_train_batch_size: 4
```

## FastAPI service

```bash
cd ml_service
uvicorn app:app --host 0.0.0.0 --port 8001
```

Проверка API:

```bash
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Текст для проверки\"}"
```

## Docker

Собирать из корня `AiDetectionML`:

```bash
docker build -f ml_service/Dockerfile -t ai-detection-ml .
docker run -p 8001:8001 ai-detection-ml
```

## Выходные артефакты

После подготовки данных:

```text
data/processed/train_ru.jsonl
data/processed/valid_ru.jsonl
data/processed/test_ru.jsonl
data/processed/dataset_stats.json
artifacts/reports/dataset_report.md
```

После обучения и оценки:

```text
models/rubert_tiny2_ai_detector/
  config.json
  model.safetensors или pytorch_model.bin
  tokenizer files
  metrics.json
  confusion_matrix.png
  label_map.json
  training_args.json

artifacts/reports/training_report.md
```

## Ограничения

- модель пилотная;
- результат вероятностный;
- нельзя использовать как доказательство нарушения;
- датасет внешний, открытый и размеченный;
- первая версия обучается только на русскоязычной части LLMTrace;
- промышленная версия требует расширенного тестирования.

