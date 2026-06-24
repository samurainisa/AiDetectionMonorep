from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("TRANSFORMERS_NO_TORCHVISION", "1")
os.environ.setdefault("TRANSFORMERS_NO_TORCHAUDIO", "1")

_ORIGINAL_FIND_SPEC = importlib.util.find_spec


def _find_spec_without_broken_vision(name, *args, **kwargs):
    if name.startswith(("torchvision", "torchaudio")):
        return None
    return _ORIGINAL_FIND_SPEC(name, *args, **kwargs)


importlib.util.find_spec = _find_spec_without_broken_vision

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import torch
import yaml
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from tqdm import tqdm
from transformers import AutoModelForSequenceClassification, AutoTokenizer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "train_config.yaml"
REPORTS_DIR = PROJECT_ROOT / "artifacts" / "reports"
LIMITATIONS = [
    "pilot model",
    "not production-ready",
    "result is probabilistic",
    "cannot be used as proof of academic misconduct",
    "trained only on the Russian subset in the first version",
]


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row.get("text"), str) and row.get("label") in {0, 1}:
                rows.append(row)
    return rows


def predict_batches(model, tokenizer, texts: list[str], batch_size: int, max_length: int, device: str) -> np.ndarray:
    probabilities: list[np.ndarray] = []
    model.eval()
    for start in tqdm(range(0, len(texts), batch_size), desc="evaluate", unit=" batch"):
        batch_texts = texts[start : start + batch_size]
        encoded = tokenizer(
            batch_texts,
            truncation=True,
            padding=True,
            max_length=max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            logits = model(**encoded).logits
            probs = torch.softmax(logits, dim=-1).detach().cpu().numpy()
        probabilities.append(probs)
    return np.vstack(probabilities)


def save_confusion_matrix(path: Path, y_true: list[int], y_pred: list[int]) -> None:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(5, 4))
    image = ax.imshow(cm, cmap="Blues")
    ax.figure.colorbar(image, ax=ax)
    ax.set(
        xticks=[0, 1],
        yticks=[0, 1],
        xticklabels=["human", "ai"],
        yticklabels=["human", "ai"],
        ylabel="True label",
        xlabel="Predicted label",
        title="Confusion matrix",
    )
    for row in range(cm.shape[0]):
        for col in range(cm.shape[1]):
            ax.text(col, row, int(cm[row, col]), ha="center", va="center", color="black")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    config = load_config()
    output_dir = PROJECT_ROOT / config["output_dir"]
    test_path = PROJECT_ROOT / config["data"]["test_path"]
    train_path = PROJECT_ROOT / config["data"]["train_path"]
    valid_path = PROJECT_ROOT / config["data"]["valid_path"]

    if not output_dir.exists():
        raise FileNotFoundError(f"Не найдена обученная модель: {output_dir}")

    test_rows = load_jsonl(test_path)
    if not test_rows:
        raise RuntimeError("test_ru.jsonl пустой. Сначала запустите scripts/02_prepare_dataset.py")

    train_size = len(load_jsonl(train_path)) if train_path.exists() else 0
    valid_size = len(load_jsonl(valid_path)) if valid_path.exists() else 0
    test_size = len(test_rows)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(output_dir)
    model = AutoModelForSequenceClassification.from_pretrained(output_dir).to(device)

    texts = [row["text"] for row in test_rows]
    y_true = [int(row["label"]) for row in test_rows]
    probabilities = predict_batches(
        model,
        tokenizer,
        texts,
        int(config["training"]["per_device_eval_batch_size"]),
        int(config["training"]["max_length"]),
        device,
    )
    y_pred = probabilities.argmax(axis=1).tolist()

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="binary",
        zero_division=0,
    )
    accuracy = accuracy_score(y_true, y_pred)

    metrics = {
        "model": "rubert_tiny2_ai_detector",
        "base_model": config["model_name"],
        "task": "binary_text_classification",
        "labels": {"0": "human", "1": "ai"},
        "dataset": {
            "train_size": train_size,
            "valid_size": valid_size,
            "test_size": test_size,
        },
        "metrics": {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
        },
        "limitations": LIMITATIONS,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    cm_path = output_dir / "confusion_matrix.png"
    save_confusion_matrix(cm_path, y_true, y_pred)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "training_report.md"
    report = [
        "# Training Report",
        "",
        f"- Base model: `{config['model_name']}`",
        "- Task: binary text classification",
        f"- Train size: {train_size}",
        f"- Valid size: {valid_size}",
        f"- Test size: {test_size}",
        "",
        "## Metrics",
        "",
        f"- Accuracy: {accuracy:.4f}",
        f"- Precision: {precision:.4f}",
        f"- Recall: {recall:.4f}",
        f"- F1: {f1:.4f}",
        "",
        "## Ограничения",
        "",
        "- модель пилотная;",
        "- результат вероятностный;",
        "- нельзя использовать как доказательство нарушения;",
        "- датасет внешний, открытый и размеченный;",
        "- первая версия обучается только на русскоязычной части;",
        "- промышленная версия требует расширенного тестирования.",
        "",
    ]
    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"[OK] Метрики сохранены: {metrics_path.relative_to(PROJECT_ROOT)}")
    print(f"[OK] Confusion matrix: {cm_path.relative_to(PROJECT_ROOT)}")
    print(f"[OK] Отчет сохранен: {report_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
