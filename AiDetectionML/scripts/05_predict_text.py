from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ml_service.src.predictor import LocalAiDetector


def main() -> None:
    parser = argparse.ArgumentParser(description="Local AI text detector CLI")
    parser.add_argument("--text", required=True, help="Текст для проверки")
    parser.add_argument(
        "--model-dir",
        default=str(PROJECT_ROOT / "models" / "rubert_tiny2_ai_detector"),
        help="Путь к сохраненной модели",
    )
    args = parser.parse_args()

    detector = LocalAiDetector(model_dir=Path(args.model_dir))
    result = detector.predict(args.text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

