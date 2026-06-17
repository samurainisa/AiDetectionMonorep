"""
Сборщик датасета для обучения модели детекции ИИ
"""
from training.enhanced_dataset_collector import EnhancedDatasetCollector, TextFeatureExtractor

# Экспортируем основные классы для использования в других модулях
__all__ = ['EnhancedDatasetCollector', 'TextFeatureExtractor'] 