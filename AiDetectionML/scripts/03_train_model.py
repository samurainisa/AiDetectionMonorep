from __future__ import annotations

import inspect
import importlib.util
import json
import os
import random
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

import numpy as np
import torch
import yaml
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "train_config.yaml"


class JsonlTextDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], tokenizer, max_length: int) -> None:
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        row = self.rows[index]
        encoded = self.tokenizer(
            row["text"],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        item = {key: value.squeeze(0) for key, value in encoded.items()}
        item["labels"] = torch.tensor(int(row["label"]), dtype=torch.long)
        return item


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Не найден processed файл: {path}")

    rows: list[dict[str, Any]] = []
    bad_lines = 0
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                bad_lines += 1
                continue
            if isinstance(row.get("text"), str) and row.get("label") in {0, 1}:
                rows.append(row)
    if bad_lines:
        print(f"[WARN] {path.name}: пропущено битых строк: {bad_lines}")
    return rows


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def compute_metrics(eval_pred) -> dict[str, float]:
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        preds,
        average="binary",
        zero_division=0,
    )
    accuracy = accuracy_score(labels, preds)
    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def build_training_args(output_dir: Path, training_config: dict[str, Any]) -> TrainingArguments:
    kwargs: dict[str, Any] = {
        "output_dir": str(output_dir),
        "num_train_epochs": training_config["num_train_epochs"],
        "per_device_train_batch_size": training_config["per_device_train_batch_size"],
        "per_device_eval_batch_size": training_config["per_device_eval_batch_size"],
        "learning_rate": training_config["learning_rate"],
        "weight_decay": training_config["weight_decay"],
        "logging_steps": 50,
        "save_strategy": "epoch",
        "seed": training_config["seed"],
        "fp16": bool(training_config.get("fp16", False)) and torch.cuda.is_available(),
        "report_to": [],
        "do_train": True,
        "do_eval": True,
        "optim": "adamw_torch",
    }

    params = inspect.signature(TrainingArguments.__init__).parameters
    if "eval_strategy" in params:
        kwargs["eval_strategy"] = "epoch"
    else:
        kwargs["evaluation_strategy"] = "epoch"

    kwargs = {key: value for key, value in kwargs.items() if key in params}
    return TrainingArguments(**kwargs)


def main() -> None:
    config = load_config()
    training_config = config["training"]
    seed = int(training_config.get("seed", 42))
    set_seed(seed)

    train_path = PROJECT_ROOT / config["data"]["train_path"]
    valid_path = PROJECT_ROOT / config["data"]["valid_path"]
    output_dir = PROJECT_ROOT / config["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    train_rows = load_jsonl(train_path)
    valid_rows = load_jsonl(valid_path)
    if not train_rows or not valid_rows:
        raise RuntimeError("Processed train/valid пустые. Сначала запустите scripts/02_prepare_dataset.py")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] Устройство: {device}")
    print(f"[INFO] train={len(train_rows)}, valid={len(valid_rows)}")
    print(f"[INFO] Базовая модель: {config['model_name']}")

    tokenizer = AutoTokenizer.from_pretrained(config["model_name"])
    model = AutoModelForSequenceClassification.from_pretrained(
        config["model_name"],
        num_labels=2,
        id2label={0: "human", 1: "ai"},
        label2id={"human": 0, "ai": 1},
    )

    max_length = int(training_config["max_length"])
    train_dataset = JsonlTextDataset(train_rows, tokenizer, max_length)
    valid_dataset = JsonlTextDataset(valid_rows, tokenizer, max_length)

    args = build_training_args(output_dir, training_config)
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=valid_dataset,
        compute_metrics=compute_metrics,
    )

    print("[INFO] Старт обучения")
    trainer.train()
    eval_metrics = trainer.evaluate()
    print(f"[OK] Eval metrics: {eval_metrics}")

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    label_map = {"human": 0, "ai": 1, "id2label": {"0": "human", "1": "ai"}}
    (output_dir / "label_map.json").write_text(
        json.dumps(label_map, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    training_args = {
        "base_model": config["model_name"],
        "output_dir": config["output_dir"],
        "device": device,
        "train_size": len(train_rows),
        "valid_size": len(valid_rows),
        "config": config,
        "eval_metrics": {key: float(value) for key, value in eval_metrics.items() if isinstance(value, (int, float))},
    }
    (output_dir / "training_args.json").write_text(
        json.dumps(training_args, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[DONE] Модель и tokenizer сохранены в {output_dir.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
