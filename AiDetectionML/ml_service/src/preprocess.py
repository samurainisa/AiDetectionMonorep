from __future__ import annotations

import os
import re
from typing import Any


MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "200000"))


def preprocess_text(value: Any, max_length: int = MAX_TEXT_LENGTH) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", "\n")
    lines = [" ".join(line.split()) for line in text.split("\n")]
    lines = [line for line in lines if line]
    text = "\n".join(lines)
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text[:max_length]
