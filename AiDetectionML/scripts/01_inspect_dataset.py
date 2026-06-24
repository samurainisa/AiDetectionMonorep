from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_SPLITS = {
    "train": PROJECT_ROOT / "train.jsonl",
    "valid": PROJECT_ROOT / "valid.jsonl",
    "test": PROJECT_ROOT / "test.jsonl",
}
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "artifacts" / "reports"
LIMITATIONS = [
    "модель пилотная",
    "результат вероятностный",
    "нельзя использовать как доказательство нарушения",
    "датасет внешний, открытый и размеченный",
    "первая версия обучается только на русскоязычной части",
    "промышленная версия требует расширенного тестирования",
]


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
                continue
    if bad_lines:
        print(f"[WARN] {path.name}: пропущено битых строк: {bad_lines}")


def inspect_split(split: str, path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Не найден файл: {path}")

    label_counts: Counter[str] = Counter()
    lang_counts: Counter[str] = Counter()
    data_type_counts: Counter[str] = Counter()
    text_lengths: list[int] = []
    total = 0
    bad_or_empty_text = 0

    print(f"[INFO] Читаю {split}: {path.name}")
    for row, _line_no in tqdm(safe_jsonl(path), desc=f"inspect {split}", unit=" rows"):
        total += 1
        label_counts[str(row.get("label", "missing"))] += 1
        lang_counts[str(row.get("lang", "missing"))] += 1
        data_type_counts[str(row.get("data_type", "missing"))] += 1

        text = row.get("text")
        if not isinstance(text, str) or not text.strip():
            bad_or_empty_text += 1
            continue
        text_lengths.append(len(text))

    stats = {
        "rows": total,
        "bad_or_empty_text": bad_or_empty_text,
        "label_distribution": dict(label_counts.most_common()),
        "lang_distribution": dict(lang_counts.most_common()),
        "data_type_distribution": dict(data_type_counts.most_common()),
        "text_length": {
            "avg": round(sum(text_lengths) / len(text_lengths), 2) if text_lengths else 0,
            "median": statistics.median(text_lengths) if text_lengths else 0,
            "min": min(text_lengths) if text_lengths else 0,
            "max": max(text_lengths) if text_lengths else 0,
        },
    }
    print(f"[OK] {split}: строк={total}, текстов={len(text_lengths)}")
    return stats


def write_report(stats: dict[str, Any]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    stats_path = PROCESSED_DIR / "dataset_stats.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# LLMTrace Dataset Report",
        "",
        "Отчет сформирован скриптом `scripts/01_inspect_dataset.py`.",
        "",
    ]
    for split, split_stats in stats.items():
        lines.extend(
            [
                f"## {split}",
                "",
                f"- Строк: {split_stats['rows']}",
                f"- Пустой/некорректный текст: {split_stats['bad_or_empty_text']}",
                f"- Средняя длина текста: {split_stats['text_length']['avg']}",
                f"- Медианная длина текста: {split_stats['text_length']['median']}",
                f"- Min/Max длина текста: {split_stats['text_length']['min']} / {split_stats['text_length']['max']}",
                "",
                "### Labels",
                "",
            ]
        )
        for label, count in split_stats["label_distribution"].items():
            lines.append(f"- `{label}`: {count}")

        lines.extend(["", "### Languages", ""])
        for lang, count in split_stats["lang_distribution"].items():
            lines.append(f"- `{lang}`: {count}")

        lines.extend(["", "### Data types", ""])
        for data_type, count in list(split_stats["data_type_distribution"].items())[:30]:
            lines.append(f"- `{data_type}`: {count}")
        lines.append("")

    lines.extend(["## Ограничения", ""])
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.append("")

    report_path = REPORTS_DIR / "dataset_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"[OK] Сохранено: {stats_path}")
    print(f"[OK] Сохранено: {report_path}")


def main() -> None:
    print("[INFO] Инспекция LLMTrace JSONL")
    stats = {split: inspect_split(split, path) for split, path in RAW_SPLITS.items()}
    write_report(stats)
    print("[DONE] Инспекция завершена")


if __name__ == "__main__":
    main()

