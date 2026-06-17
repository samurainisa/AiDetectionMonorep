"""
Модуль обучения модели детектора ИИ

Содержит инструменты для ручного обучения модели на CSV/JSON датасетах.
"""

from .manual_training import SimpleTrainer

__version__ = "1.0.0"
__all__ = ["SimpleTrainer"] 