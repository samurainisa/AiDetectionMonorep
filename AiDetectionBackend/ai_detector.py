"""
Модуль собственного детектора ИИ-контента на базе DeBERTa
Реализует архитектуру самообучающейся системы с использованием Pangram API как учителя
"""

import os
import json
import torch
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import pickle
import logging

from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback
)
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from sklearn.model_selection import train_test_split
import torch.nn.functional as F

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Конфигурация для обучения модели"""
    model_name: str = "microsoft/deberta-v3-base"
    max_length: int = 512
    batch_size: int = 16
    learning_rate: float = 2e-5
    num_epochs: int = 3
    warmup_steps: int = 500
    weight_decay: float = 0.01
    early_stopping_patience: int = 2
    min_samples_for_training: int = 5
    validation_split: float = 0.2
    test_split: float = 0.1
    confidence_threshold: float = 0.85  # Корреляция с учителем для активации

@dataclass
class PredictionResult:
    """Результат предсказания модели"""
    ai_probability: float
    confidence: float
    prediction_source: str  # 'local' или 'pangram'
    processing_time: float
    model_version: Optional[str] = None

class AIDetectionDataset(Dataset):
    """Dataset для обучения детектора ИИ"""
    
    def __init__(self, texts: List[str], labels: List[float], tokenizer, max_length: int = 512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = float(self.labels[idx])
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.float)
        }

class ModelMetrics:
    """Класс для отслеживания метрик модели"""
    
    def __init__(self):
        self.training_history: List[Dict] = []
        self.validation_scores: List[float] = []
        self.correlation_with_teacher: List[float] = []
        self.calibration_errors: List[float] = []
        
    def add_training_epoch(self, epoch: int, train_loss: float, val_loss: float, 
                          val_accuracy: float, correlation: float):
        """Добавляет метрики эпохи обучения"""
        self.training_history.append({
            'epoch': epoch,
            'train_loss': train_loss,
            'val_loss': val_loss,
            'val_accuracy': val_accuracy,
            'correlation': correlation,
            'timestamp': datetime.now().isoformat()
        })
        
    def calculate_ece(self, predictions: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
        """Вычисляет Expected Calibration Error"""
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]
        
        ece = 0
        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            in_bin = (predictions > bin_lower) & (predictions <= bin_upper)
            prop_in_bin = in_bin.mean()
            
            if prop_in_bin > 0:
                accuracy_in_bin = labels[in_bin].mean()
                avg_confidence_in_bin = predictions[in_bin].mean()
                ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
                
        return ece

class LocalAIDetector:
    """Локальный детектор ИИ на базе DeBERTa"""
    
    def __init__(self, config: TrainingConfig, model_dir: str = "models/ai_detector"):
        self.config = config
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.tokenizer = None
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.metrics = ModelMetrics()
        self.is_trained = False
        self.model_version = "v1.0"
        
        # Пути к файлам
        self.model_path = self.model_dir / "pytorch_model.bin"
        self.config_path = self.model_dir / "config.json"
        self.tokenizer_path = self.model_dir / "tokenizer"
        self.metrics_path = self.model_dir / "metrics.pkl"
        
        logger.info(f"Инициализирован LocalAIDetector с устройством: {self.device}")
        
    def _load_tokenizer(self):
        """Загружает токенизатор"""
        if self.tokenizer_path.exists():
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.tokenizer_path))
            logger.info("Загружен сохраненный токенизатор")
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            logger.info(f"Загружен токенизатор из {self.config.model_name}")
            
    def _load_model(self):
        """Загружает модель"""
        if self.model_path.exists():
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(self.model_dir),
                num_labels=1,
                problem_type="regression"
            )
            self.is_trained = True
            logger.info("Загружена обученная модель")
        else:
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.config.model_name,
                num_labels=1,
                problem_type="regression"
            )
            logger.info(f"Загружена базовая модель {self.config.model_name}")
            
        self.model.to(self.device)
        
    def _save_model(self):
        """Сохраняет модель и токенизатор"""
        self.model.save_pretrained(str(self.model_dir))
        self.tokenizer.save_pretrained(str(self.tokenizer_path))
        
        # Сохраняем метрики
        with open(self.metrics_path, 'wb') as f:
            pickle.dump(self.metrics, f)
            
        logger.info(f"Модель сохранена в {self.model_dir}")
        
    def _load_metrics(self):
        """Загружает метрики"""
        if self.metrics_path.exists():
            with open(self.metrics_path, 'rb') as f:
                self.metrics = pickle.load(f)
                
    def initialize(self):
        """Инициализирует модель и токенизатор"""
        self._load_tokenizer()
        self._load_model()
        self._load_metrics()
        
    def prepare_training_data(self, db_connection) -> Tuple[List[str], List[float]]:
        """Подготавливает данные для обучения из базы данных"""
        # SQL запрос для получения данных с оценками Pangram API
        query = """
        SELECT extracted_text, ai_likelihood, created_at
        FROM detection 
        WHERE ai_likelihood IS NOT NULL 
        AND LENGTH(extracted_text) > 100
        AND created_at > date('now', '-6 months')
        ORDER BY created_at DESC
        """
        
        cursor = db_connection.execute(query)
        rows = cursor.fetchall()
        
        texts = []
        labels = []
        
        for row in rows:
            text = row[0]
            ai_likelihood = row[1]
            
            # Фильтруем тексты с неуверенными оценками (40-60%)
            if 0.1 <= ai_likelihood <= 0.9:  # Исключаем крайние значения
                texts.append(text)
                labels.append(ai_likelihood)
                
        logger.info(f"Подготовлено {len(texts)} образцов для обучения")
        return texts, labels
        
    def train(self, texts: List[str], labels: List[float]) -> Dict[str, Any]:
        """Обучает модель на подготовленных данных"""
        if len(texts) < self.config.min_samples_for_training:
            raise ValueError(f"Недостаточно данных для обучения. Нужно минимум {self.config.min_samples_for_training}, получено {len(texts)}")
            
        # Разделение данных
        train_texts, temp_texts, train_labels, temp_labels = train_test_split(
            texts, labels, test_size=self.config.validation_split + self.config.test_split, 
            random_state=42, stratify=None
        )
        
        val_texts, test_texts, val_labels, test_labels = train_test_split(
            temp_texts, temp_labels, 
            test_size=self.config.test_split / (self.config.validation_split + self.config.test_split),
            random_state=42
        )
        
        # Создание датасетов
        train_dataset = AIDetectionDataset(train_texts, train_labels, self.tokenizer, self.config.max_length)
        val_dataset = AIDetectionDataset(val_texts, val_labels, self.tokenizer, self.config.max_length)
        test_dataset = AIDetectionDataset(test_texts, test_labels, self.tokenizer, self.config.max_length)
        
        # Настройка обучения
        training_args = TrainingArguments(
            output_dir=str(self.model_dir / "checkpoints"),
            num_train_epochs=self.config.num_epochs,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            warmup_steps=self.config.warmup_steps,
            weight_decay=self.config.weight_decay,
            learning_rate=self.config.learning_rate,
            logging_dir=str(self.model_dir / "logs"),
            logging_steps=100,
            evaluation_strategy="steps",
            eval_steps=500,
            save_strategy="steps",
            save_steps=500,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            report_to=None  # Отключаем wandb
        )
        
        # Создание тренера
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=self.config.early_stopping_patience)]
        )
        
        # Обучение
        logger.info("Начинаем обучение модели...")
        training_result = trainer.train()
        
        # Оценка на тестовой выборке
        test_predictions = trainer.predict(test_dataset)
        test_preds = torch.sigmoid(torch.tensor(test_predictions.predictions)).numpy().flatten()
        test_labels_array = np.array(test_labels)
        
        # Вычисление метрик
        correlation = np.corrcoef(test_preds, test_labels_array)[0, 1]
        mse = np.mean((test_preds - test_labels_array) ** 2)
        mae = np.mean(np.abs(test_preds - test_labels_array))
        ece = self.metrics.calculate_ece(test_preds, test_labels_array)
        
        # Сохранение результатов
        training_metrics = {
            'correlation_with_teacher': correlation,
            'mse': mse,
            'mae': mae,
            'ece': ece,
            'training_loss': training_result.training_loss,
            'num_samples': len(texts),
            'model_version': self.model_version,
            'training_date': datetime.now().isoformat()
        }
        
        # Обновляем статус обученности
        if correlation >= self.config.confidence_threshold:
            self.is_trained = True
            logger.info(f"Модель успешно обучена! Корреляция с учителем: {correlation:.3f}")
        else:
            logger.warning(f"Корреляция с учителем недостаточна: {correlation:.3f} < {self.config.confidence_threshold}")
            
        # Сохраняем модель
        self._save_model()
        
        return training_metrics
        
    def predict(self, text: str) -> PredictionResult:
        """Делает предсказание для текста"""
        start_time = datetime.now()
        
        if not self.is_trained:
            raise ValueError("Модель не обучена. Сначала выполните обучение.")
            
        # Токенизация
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.config.max_length,
            return_tensors='pt'
        )
        
        # Перенос на устройство
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        # Предсказание
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probability = torch.sigmoid(logits).cpu().numpy()[0][0]
            
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Вычисление уверенности (простая эвристика)
        confidence = abs(probability - 0.5) * 2  # Чем дальше от 0.5, тем выше уверенность
        
        return PredictionResult(
            ai_probability=float(probability),
            confidence=float(confidence),
            prediction_source='local',
            processing_time=processing_time,
            model_version=self.model_version
        )
        
    def batch_predict(self, texts: List[str]) -> List[PredictionResult]:
        """Пакетное предсказание"""
        results = []
        for text in texts:
            result = self.predict(text)
            results.append(result)
        return results
        
    def get_model_info(self) -> Dict[str, Any]:
        """Возвращает информацию о модели"""
        return {
            'is_trained': self.is_trained,
            'model_version': self.model_version,
            'device': str(self.device),
            'model_name': self.config.model_name,
            'last_training': self.metrics.training_history[-1] if self.metrics.training_history else None,
            'total_training_epochs': len(self.metrics.training_history),
            'model_size_mb': self._get_model_size_mb()
        }
        
    def _get_model_size_mb(self) -> float:
        """Возвращает размер модели в МБ"""
        if self.model_path.exists():
            return self.model_path.stat().st_size / (1024 * 1024)
        return 0.0

class HybridDetector:
    """Гибридный детектор, использующий локальную модель и Pangram API"""
    
    def __init__(self, local_detector: LocalAIDetector, pangram_api_caller):
        self.local_detector = local_detector
        self.pangram_api_caller = pangram_api_caller
        self.uncertainty_threshold = 0.3  # Порог неуверенности для обращения к API
        
    def predict(self, text: str, force_api: bool = False) -> PredictionResult:
        """Гибридное предсказание"""
        
        # Если модель не обучена или принудительно запрошен API
        if not self.local_detector.is_trained or force_api:
            return self._predict_with_api(text)
            
        # Получаем предсказание локальной модели
        local_result = self.local_detector.predict(text)
        
        # Если уверенность высокая, возвращаем локальный результат
        if local_result.confidence > self.uncertainty_threshold:
            return local_result
            
        # Если уверенность низкая, обращаемся к API
        api_result = self._predict_with_api(text)
        
        # Возвращаем результат API, но отмечаем как гибридный
        api_result.prediction_source = 'hybrid'
        return api_result
        
    def _predict_with_api(self, text: str) -> PredictionResult:
        """Предсказание через Pangram API"""
        start_time = datetime.now()
        
        try:
            # Здесь должен быть вызов Pangram API
            # Для примера возвращаем заглушку
            api_response = self.pangram_api_caller(text)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return PredictionResult(
                ai_probability=api_response.get('ai_likelihood', 0.5),
                confidence=0.9,  # API всегда уверенный
                prediction_source='pangram',
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обращении к Pangram API: {e}")
            # Fallback на локальную модель
            if self.local_detector.is_trained:
                result = self.local_detector.predict(text)
                result.prediction_source = 'local_fallback'
                return result
            else:
                raise Exception("API недоступен и локальная модель не обучена")

# Фабрика для создания детекторов
class DetectorFactory:
    """Фабрика для создания и настройки детекторов"""
    
    @staticmethod
    def create_local_detector(config: Optional[TrainingConfig] = None) -> LocalAIDetector:
        """Создает локальный детектор с конфигурацией по умолчанию"""
        if config is None:
            config = TrainingConfig()
            
        detector = LocalAIDetector(config)
        detector.initialize()
        return detector
        
    @staticmethod
    def create_hybrid_detector(pangram_api_caller) -> HybridDetector:
        """Создает гибридный детектор"""
        local_detector = DetectorFactory.create_local_detector()
        return HybridDetector(local_detector, pangram_api_caller) 