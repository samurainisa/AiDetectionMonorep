from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "train_config.yaml"
RAW_SPLITS = {
    "train": PROJECT_ROOT / "train.jsonl",
    "valid": PROJECT_ROOT / "valid.jsonl",
    "test": PROJECT_ROOT / "test.jsonl",
}
LABELS = {"human": 0, "ai": 1}


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def safe_jsonl(path: Path):
    bad_lines = 0
    with path.open("r", encoding="utf-8") as file:
        for line_no, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line), line_no
            except json.JSONDecodeError:
                bad_lines += 1
    if bad_lines:
        print(f"[WARN] {path.name}: пропущено битых строк: {bad_lines}")


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.replace("\r", "\n").split())


def prepare_split(split: str, raw_path: Path, output_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    data_config = config["data"]
    min_text_chars = int(data_config.get("min_text_chars", 200))
    max_per_class = data_config.get(f"max_{split}_per_class")
    max_per_class = int(max_per_class) if max_per_class is not None else None
    seed = int(config["training"].get("seed", 42))
    rng = random.Random(seed)

    buckets: dict[int, list[dict[str, Any]]] = {0: [], 1: []}
    seen_texts: set[str] = set()
    skipped: Counter[str] = Counter()

    print(f"[INFO] Подготовка split={split}, source={raw_path.name}")
    for row, _line_no in tqdm(safe_jsonl(raw_path), desc=f"prepare {split}", unit=" rows"):
        if row.get("lang") != "ru":
            skipped["not_ru"] += 1
            continue

        label_name = row.get("label")
        if label_name not in LABELS:
            skipped["bad_label"] += 1
            continue

        text = normalize_text(row.get("text"))
        if not text:
            skipped["empty_text"] += 1
            continue
        if len(text) < min_text_chars:
            skipped["too_short"] += 1
            continue
        if text in seen_texts:
            skipped["duplicate"] += 1
            continue

        label = LABELS[label_name]
        if max_per_class is not None and len(buckets[label]) >= max_per_class:
            skipped["class_limit"] += 1
            if all(len(items) >= max_per_class for items in buckets.values()):
                break
            continue

        seen_texts.add(text)
        buckets[label].append(
            {
                "text": text,
                "label": label,
                "label_name": label_name,
                "lang": "ru",
                "data_type": row.get("data_type"),
                "topic_id": row.get("topic_id"),
            }
        )

    balanced_size = min(len(buckets[0]), len(buckets[1]))
    if max_per_class is not None:
        balanced_size = min(balanced_size, max_per_class)

    prepared: list[dict[str, Any]] = []
    for label, rows in buckets.items():
        rng.shuffle(rows)
        prepared.extend(rows[:balanced_size])

    rng.shuffle(prepared)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for item in prepared:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")

    summary = {
        "output": str(output_path.relative_to(PROJECT_ROOT)),
        "rows": len(prepared),
        "per_class": balanced_size,
        "collected": {"human": len(buckets[0]), "ai": len(buckets[1])},
        "skipped": dict(skipped),
    }
    print(f"[OK] {split}: сохранено={len(prepared)}, per_class={balanced_size}")
    return summary


def main() -> None:
    config = load_config()
    processed_dir = PROJECT_ROOT / "data" / "processed"
    outputs = {
        "train": PROJECT_ROOT / config["data"]["train_path"],
        "valid": PROJECT_ROOT / config["data"]["valid_path"],
        "test": PROJECT_ROOT / config["data"]["test_path"],
    }

    summaries = {}
    for split, raw_path in RAW_SPLITS.items():
        if not raw_path.exists():
            raise FileNotFoundError(f"Не найден исходный файл: {raw_path}")
        summaries[split] = prepare_split(split, raw_path, outputs[split], config)

    processed_dir.mkdir(parents=True, exist_ok=True)
    summary_path = processed_dir / "prepare_summary.json"
    summary_path.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Сводка сохранена: {summary_path.relative_to(PROJECT_ROOT)}")
    print("[DONE] Подготовка датасета завершена")


if __name__ == "__main__":
    main()

