#!/usr/bin/env python3
"""
Полноценное обучение DeBERTa модели для детекции ИИ
"""

import pandas as pd
import numpy as np
import torch
import logging
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    TrainingArguments, Trainer, EarlyStoppingCallback
)
from torch.utils.data import Dataset
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any
import matplotlib.pyplot as plt
import seaborn as sns

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_training.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AIDetectionDataset(Dataset):
    """Датасет для обучения детекции ИИ"""
    
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
        
        # Токенизация
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

class FullAITrainer:
    """Полноценный тренер для DeBERTa модели"""
    
    def __init__(self, dataset_path: str = None, model_name: str = "microsoft/deberta-v3-base"):
        self.dataset_path = dataset_path or self._find_dataset_file()
        self.model_name = model_name
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = None
        self.model = None
        self.trainer = None
        
        logger.info(f"Устройство: {self.device}")
        logger.info(f"Модель: {model_name}")
        
    def _find_dataset_file(self) -> str:
        """Ищет последний файл датасета"""
        import glob
        import os
        
        csv_files = glob.glob("../datasets/*.csv")
        json_files = glob.glob("../datasets/*.json")
        
        all_files = csv_files + json_files
        if not all_files:
            raise FileNotFoundError("Не найдено файлов датасета в папке datasets/")
        
        latest_file = max(all_files, key=os.path.getmtime)
        logger.info(f"Найден датасет: {latest_file}")
        return latest_file
    
    def load_and_analyze_data(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Загружает и анализирует данные"""
        logger.info("Загрузка и анализ данных...")
        
        # Загрузка
        if self.dataset_path.endswith('.csv'):
            df = pd.read_csv(self.dataset_path)
        elif self.dataset_path.endswith('.json'):
            df = pd.read_json(self.dataset_path)
        else:
            raise ValueError(f"Неподдерживаемый формат: {self.dataset_path}")
        
        # Определение колонок
        text_col = None
        ai_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if 'text' in col_lower and text_col is None:
                text_col = col
            elif any(x in col_lower for x in ['ai_likelihood', 'ai_probability', 'ai_score', 'likelihood']) and ai_col is None:
                ai_col = col
        
        if text_col is None or ai_col is None:
            raise ValueError("Не найдены необходимые колонки")
        
        # Фильтрация и очистка
        df = df.dropna(subset=[text_col, ai_col])
        df = df[df[text_col].str.len() > 50]  # Минимальная длина
        df = df[df[text_col].str.len() < 5000]  # Максимальная длина
        
        # Анализ данных
        analysis = {
            'total_samples': len(df),
            'text_column': text_col,
            'ai_column': ai_col,
            'avg_text_length': df[text_col].str.len().mean(),
            'median_text_length': df[text_col].str.len().median(),
            'ai_score_distribution': {
                'mean': df[ai_col].mean(),
                'std': df[ai_col].std(),
                'min': df[ai_col].min(),
                'max': df[ai_col].max()
            }
        }
        
        # Распределение по классам
        df['binary_label'] = (df[ai_col] >= 0.5).astype(int)
        class_distribution = df['binary_label'].value_counts()
        analysis['class_distribution'] = {
            'human': int(class_distribution.get(0, 0)),
            'ai': int(class_distribution.get(1, 0)),
            'balance_ratio': class_distribution.get(1, 0) / len(df) if len(df) > 0 else 0
        }
        
        # Рекомендации по качеству данных
        analysis['data_quality'] = self._assess_data_quality(analysis)
        
        logger.info(f"Анализ данных завершен:")
        logger.info(f"  Образцов: {analysis['total_samples']}")
        logger.info(f"  Человек: {analysis['class_distribution']['human']}")
        logger.info(f"  ИИ: {analysis['class_distribution']['ai']}")
        logger.info(f"  Баланс ИИ: {analysis['class_distribution']['balance_ratio']:.2%}")
        logger.info(f"  Средняя длина: {analysis['avg_text_length']:.0f} символов")
        
        return df, analysis
    
    def _assess_data_quality(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Оценивает качество данных для обучения"""
        total = analysis['total_samples']
        balance = analysis['class_distribution']['balance_ratio']
        
        # Оценка размера датасета
        if total < 1000:
            size_quality = "Критически мало"
            size_recommendation = "Нужно минимум 1000 образцов"
        elif total < 5000:
            size_quality = "Недостаточно"
            size_recommendation = "Рекомендуется 5000+ образцов для хорошего качества"
        elif total < 20000:
            size_quality = "Приемлемо"
            size_recommendation = "Можно обучать, но больше данных улучшит качество"
        else:
            size_quality = "Отлично"
            size_recommendation = "Достаточно данных для качественного обучения"
        
        # Оценка баланса классов
        if 0.3 <= balance <= 0.7:
            balance_quality = "Хороший баланс"
            balance_recommendation = "Баланс классов оптимальный"
        elif 0.2 <= balance <= 0.8:
            balance_quality = "Приемлемый дисбаланс"
            balance_recommendation = "Небольшой дисбаланс, можно использовать взвешивание"
        else:
            balance_quality = "Сильный дисбаланс"
            balance_recommendation = "Критический дисбаланс, нужна аугментация данных"
        
        return {
            'size_quality': size_quality,
            'size_recommendation': size_recommendation,
            'balance_quality': balance_quality,
            'balance_recommendation': balance_recommendation,
            'overall_feasible': total >= 1000 and 0.1 <= balance <= 0.9
        }
    
    def prepare_model_and_tokenizer(self):
        """Подготавливает модель и токенизатор"""
        logger.info(f"Загрузка модели {self.model_name}...")
        
        try:
            # Токенизатор
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Модель для регрессии (предсказание вероятности 0-1)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                num_labels=1,  # Регрессия
                problem_type="regression"
            )
            
            self.model.to(self.device)
            logger.info(f"Модель загружена на {self.device}")
            
            # Информация о модели
            total_params = sum(p.numel() for p in self.model.parameters())
            trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
            
            logger.info(f"Параметров всего: {total_params:,}")
            logger.info(f"Обучаемых параметров: {trainable_params:,}")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            raise
    
    def split_data(self, df: pd.DataFrame, analysis: Dict[str, Any], 
                   test_size: float = 0.2, val_size: float = 0.1) -> Tuple[Any, Any, Any]:
        """Разделяет данные на train/val/test"""
        text_col = analysis['text_column']
        ai_col = analysis['ai_column']
        
        texts = df[text_col].tolist()
        labels = df[ai_col].tolist()
        
        # Стратификация по бинарным меткам для лучшего баланса
        binary_labels = (df[ai_col] >= 0.5).astype(int)
        
        # Train + Val / Test
        X_temp, X_test, y_temp, y_test, strat_temp, strat_test = train_test_split(
            texts, labels, binary_labels, 
            test_size=test_size, 
            stratify=binary_labels, 
            random_state=42
        )
        
        # Train / Val
        val_size_adjusted = val_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, 
            test_size=val_size_adjusted, 
            stratify=strat_temp, 
            random_state=42
        )
        
        logger.info(f"Разделение данных:")
        logger.info(f"  Train: {len(X_train)} образцов")
        logger.info(f"  Validation: {len(X_val)} образцов")
        logger.info(f"  Test: {len(X_test)} образцов")
        
        # Создание датасетов
        train_dataset = AIDetectionDataset(X_train, y_train, self.tokenizer)
        val_dataset = AIDetectionDataset(X_val, y_val, self.tokenizer)
        test_dataset = AIDetectionDataset(X_test, y_test, self.tokenizer)
        
        return train_dataset, val_dataset, test_dataset
    
    def setup_training(self, train_dataset, val_dataset, output_dir: str = "./ai_detector_model"):
        """Настраивает параметры обучения"""
        
        # Автоматический подбор batch_size в зависимости от размера данных
        dataset_size = len(train_dataset)
        if dataset_size < 1000:
            batch_size = 8
            num_epochs = 5
        elif dataset_size < 5000:
            batch_size = 16
            num_epochs = 4
        else:
            batch_size = 32 if self.device.type == 'cuda' else 16
            num_epochs = 3
        
        # Настройки обучения
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            warmup_steps=min(500, len(train_dataset) // batch_size),
            weight_decay=0.01,
            logging_dir=f'{output_dir}/logs',
            logging_steps=10,
            evaluation_strategy="steps",
            eval_steps=50,
            save_strategy="steps",
            save_steps=100,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            save_total_limit=3,
            dataloader_pin_memory=False,  # Для совместимости
            remove_unused_columns=False,
            report_to=None  # Отключаем wandb/tensorboard
        )
        
        # Функция для вычисления метрик
        def compute_metrics(eval_pred):
            predictions, labels = eval_pred
            predictions = predictions.flatten()
            
            # Ограничиваем предсказания в диапазоне [0, 1]
            predictions = np.clip(predictions, 0, 1)
            
            # Бинарные предсказания
            binary_preds = (predictions >= 0.5).astype(int)
            binary_labels = (labels >= 0.5).astype(int)
            
            # Метрики
            accuracy = accuracy_score(binary_labels, binary_preds)
            precision, recall, f1, _ = precision_recall_fscore_support(
                binary_labels, binary_preds, average='binary'
            )
            
            try:
                auc = roc_auc_score(binary_labels, predictions)
            except:
                auc = 0.5
            
            # MSE для регрессии
            mse = np.mean((predictions - labels) ** 2)
            mae = np.mean(np.abs(predictions - labels))
            
            return {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'auc': auc,
                'mse': mse,
                'mae': mae
            }
        
        # Создание тренера
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=compute_metrics,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
        )
        
        logger.info(f"Настройки обучения:")
        logger.info(f"  Batch size: {batch_size}")
        logger.info(f"  Epochs: {num_epochs}")
        logger.info(f"  Warmup steps: {training_args.warmup_steps}")
    
    def train_model(self) -> Dict[str, Any]:
        """Обучает модель"""
        logger.info("Начинаем обучение модели...")
        start_time = time.time()
        
        try:
            # Обучение
            train_result = self.trainer.train()
            
            # Сохранение модели
            self.trainer.save_model()
            self.tokenizer.save_pretrained(self.trainer.args.output_dir)
            
            training_time = time.time() - start_time
            
            logger.info(f"Обучение завершено за {training_time:.1f} секунд")
            logger.info(f"Финальный train loss: {train_result.training_loss:.4f}")
            
            return {
                'training_loss': train_result.training_loss,
                'training_time': training_time,
                'model_path': self.trainer.args.output_dir
            }
            
        except Exception as e:
            logger.error(f"Ошибка обучения: {e}")
            raise
    
    def evaluate_model(self, test_dataset) -> Dict[str, Any]:
        """Оценивает модель на тестовой выборке"""
        logger.info("Оценка модели на тестовой выборке...")
        
        # Оценка
        eval_result = self.trainer.evaluate(test_dataset)
        
        # Предсказания для анализа
        predictions = self.trainer.predict(test_dataset)
        preds = np.clip(predictions.predictions.flatten(), 0, 1)
        labels = predictions.label_ids
        
        # Дополнительная аналитика
        correlation = np.corrcoef(preds, labels)[0, 1]
        
        results = {
            'test_accuracy': eval_result['eval_accuracy'],
            'test_precision': eval_result['eval_precision'],
            'test_recall': eval_result['eval_recall'],
            'test_f1': eval_result['eval_f1'],
            'test_auc': eval_result['eval_auc'],
            'test_mse': eval_result['eval_mse'],
            'test_mae': eval_result['eval_mae'],
            'correlation': correlation,
            'predictions_sample': preds[:10].tolist(),
            'labels_sample': labels[:10].tolist()
        }
        
        logger.info("Результаты на тестовой выборке:")
        logger.info(f"  Accuracy: {results['test_accuracy']:.3f}")
        logger.info(f"  Precision: {results['test_precision']:.3f}")
        logger.info(f"  Recall: {results['test_recall']:.3f}")
        logger.info(f"  F1: {results['test_f1']:.3f}")
        logger.info(f"  AUC: {results['test_auc']:.3f}")
        logger.info(f"  MSE: {results['test_mse']:.4f}")
        logger.info(f"  Correlation: {correlation:.3f}")
        
        return results
    
    def save_results(self, analysis: Dict, train_results: Dict, test_results: Dict):
        """Сохраняет результаты обучения"""
        full_results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'model_name': self.model_name,
            'dataset_path': self.dataset_path,
            'device': str(self.device),
            'data_analysis': analysis,
            'training_results': train_results,
            'test_results': test_results
        }
        
        results_file = Path("full_training_results.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(full_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Результаты сохранены в {results_file}")

def main():
    """Основная функция полноценного обучения"""
    print("🤖 Полноценное обучение DeBERTa для детекции ИИ")
    print("=" * 60)
    
    try:
        # Инициализация
        trainer = FullAITrainer()
        
        # Загрузка и анализ данных
        df, analysis = trainer.load_and_analyze_data()
        
        # Проверка готовности к обучению
        if not analysis['data_quality']['overall_feasible']:
            print("❌ Данные не готовы для обучения:")
            print(f"   {analysis['data_quality']['size_recommendation']}")
            print(f"   {analysis['data_quality']['balance_recommendation']}")
            return
        
        print(f"✅ Данные готовы к обучению")
        print(f"   {analysis['data_quality']['size_quality']}: {analysis['total_samples']} образцов")
        print(f"   {analysis['data_quality']['balance_quality']}")
        
        # Подготовка модели
        trainer.prepare_model_and_tokenizer()
        
        # Разделение данных
        train_dataset, val_dataset, test_dataset = trainer.split_data(df, analysis)
        
        # Настройка обучения
        trainer.setup_training(train_dataset, val_dataset)
        
        # Обучение
        train_results = trainer.train_model()
        
        # Тестирование
        test_results = trainer.evaluate_model(test_dataset)
        
        # Сохранение результатов
        trainer.save_results(analysis, train_results, test_results)
        
        print("\n🎉 Обучение успешно завершено!")
        print(f"📊 F1-score: {test_results['test_f1']:.3f}")
        print(f"📊 Accuracy: {test_results['test_accuracy']:.3f}")
        print(f"📊 Correlation: {test_results['correlation']:.3f}")
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()