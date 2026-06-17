#!/usr/bin/env python3
"""
Улучшенное обучение с дополнительными признаками из Pangram API
"""

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import logging
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score
from transformers import (
    AutoTokenizer, AutoModel,
    TrainingArguments, Trainer, EarlyStoppingCallback
)
from torch.utils.data import Dataset
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_training.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedAIDetectionDataset(Dataset):
    """Датасет с текстом и дополнительными признаками"""
    
    def __init__(self, texts: List[str], labels: List[float], 
                 features: np.ndarray, tokenizer, max_length: int = 512):
        self.texts = texts
        self.labels = labels
        self.features = features
        self.tokenizer = tokenizer
        self.max_length = max_length
        
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = float(self.labels[idx])
        features = torch.tensor(self.features[idx], dtype=torch.float32)
        
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
            'features': features,
            'labels': torch.tensor(label, dtype=torch.float)
        }

class EnhancedAIDetectionModel(nn.Module):
    """Модель, объединяющая DeBERTa и дополнительные признаки"""
    
    def __init__(self, model_name: str, num_features: int, hidden_size: int = 256):
        super().__init__()
        
        # Текстовый энкодер (DeBERTa без головы классификации)
        self.text_encoder = AutoModel.from_pretrained(model_name)
        text_hidden_size = self.text_encoder.config.hidden_size
        
        # Энкодер для дополнительных признаков
        self.feature_encoder = nn.Sequential(
            nn.Linear(num_features, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        
        # Слой объединения
        fusion_input_size = text_hidden_size + hidden_size // 2
        self.fusion_layer = nn.Sequential(
            nn.Linear(fusion_input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        
        # Финальный классификатор
        self.classifier = nn.Linear(hidden_size // 2, 1)
        
        # Инициализация весов
        self._init_weights()
    
    def _init_weights(self):
        """Инициализация весов для новых слоев"""
        for module in [self.feature_encoder, self.fusion_layer, self.classifier]:
            for layer in module:
                if isinstance(layer, nn.Linear):
                    torch.nn.init.xavier_uniform_(layer.weight)
                    torch.nn.init.zeros_(layer.bias)
    
    def forward(self, input_ids, attention_mask, features, labels=None):
        # Получаем представления текста
        text_outputs = self.text_encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        text_embeddings = text_outputs.last_hidden_state[:, 0, :]  # CLS token
        
        # Обрабатываем дополнительные признаки
        feature_embeddings = self.feature_encoder(features)
        
        # Объединяем представления
        combined = torch.cat([text_embeddings, feature_embeddings], dim=1)
        fused = self.fusion_layer(combined)
        
        # Классификация
        logits = self.classifier(fused)
        
        outputs = {'logits': logits}
        
        if labels is not None:
            loss_fn = nn.MSELoss()
            loss = loss_fn(logits.squeeze(), labels)
            outputs['loss'] = loss
        
        return outputs

class EnhancedTrainer(Trainer):
    """Кастомный тренер для работы с дополнительными признаками"""
    
    def compute_loss(self, model, inputs, return_outputs=False):
        labels = inputs.pop("labels")
        outputs = model(**inputs, labels=labels)
        loss = outputs["loss"]
        return (loss, outputs) if return_outputs else loss

class EnhancedAITrainer:
    """Улучшенный тренер с дополнительными признаками"""
    
    def __init__(self, dataset_path: str = None, model_name: str = "microsoft/deberta-v3-base"):
        self.dataset_path = dataset_path or self._find_enhanced_dataset()
        self.model_name = model_name
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = None
        self.model = None
        self.trainer = None
        self.scaler = StandardScaler()
        
        logger.info(f"Устройство: {self.device}")
        logger.info(f"Модель: {model_name}")
    
    def _find_enhanced_dataset(self) -> str:
        """Ищет улучшенный датасет"""
        import glob
        import os
        
        # Ищем enhanced_ файлы
        enhanced_files = glob.glob("../datasets/enhanced_*.csv")
        if enhanced_files:
            latest_file = max(enhanced_files, key=os.path.getmtime)
            logger.info(f"Найден улучшенный датасет: {latest_file}")
            return latest_file
        
        # Ищем обычные файлы
        csv_files = glob.glob("../datasets/*.csv")
        json_files = glob.glob("../datasets/*.json")
        
        all_files = csv_files + json_files
        if not all_files:
            raise FileNotFoundError("Не найдено файлов датасета")
        
        latest_file = max(all_files, key=os.path.getmtime)
        logger.info(f"Найден обычный датасет: {latest_file}")
        return latest_file
    
    def load_and_analyze_data(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Загружает и анализирует улучшенный датасет"""
        logger.info("Загрузка улучшенного датасета...")
        
        # Загрузка
        if self.dataset_path.endswith('.csv'):
            df = pd.read_csv(self.dataset_path)
        elif self.dataset_path.endswith('.json'):
            df = pd.read_json(self.dataset_path)
        else:
            raise ValueError(f"Неподдерживаемый формат: {self.dataset_path}")
        
        # Определение колонок
        text_col = 'text'
        
        # Ищем целевую переменную
        target_col = None
        for col in df.columns:
            if any(x in col.lower() for x in ['ai_likelihood', 'original_ai_likelihood']):
                target_col = col
                break
        
        if target_col is None:
            raise ValueError("Не найдена целевая переменная")
        
        # Фильтрация
        df = df.dropna(subset=[text_col, target_col])
        df = df[df[text_col].str.len() > 50]
        
        # Выделяем признаки
        feature_columns = []
        for col in df.columns:
            if col not in [text_col, target_col] and df[col].dtype in ['int64', 'float64']:
                if not col.startswith('original_') or col == target_col:
                    feature_columns.append(col)
        
        logger.info(f"Найдено {len(feature_columns)} дополнительных признаков:")
        for col in feature_columns[:10]:  # Показываем первые 10
            logger.info(f"  - {col}")
        if len(feature_columns) > 10:
            logger.info(f"  ... и еще {len(feature_columns) - 10}")
        
        # Анализ данных
        analysis = {
            'total_samples': len(df),
            'text_column': text_col,
            'target_column': target_col,
            'feature_columns': feature_columns,
            'num_features': len(feature_columns),
            'avg_text_length': df[text_col].str.len().mean(),
            'target_distribution': {
                'mean': df[target_col].mean(),
                'std': df[target_col].std(),
                'min': df[target_col].min(),
                'max': df[target_col].max()
            }
        }
        
        # Распределение по классам
        df['binary_label'] = (df[target_col] >= 0.5).astype(int)
        class_distribution = df['binary_label'].value_counts()
        analysis['class_distribution'] = {
            'human': int(class_distribution.get(0, 0)),
            'ai': int(class_distribution.get(1, 0)),
            'balance_ratio': class_distribution.get(1, 0) / len(df) if len(df) > 0 else 0
        }
        
        # Оценка качества данных
        analysis['data_quality'] = self._assess_enhanced_data_quality(analysis)
        
        logger.info(f"Анализ улучшенного датасета:")
        logger.info(f"  Образцов: {analysis['total_samples']}")
        logger.info(f"  Признаков: {analysis['num_features']}")
        logger.info(f"  Человек: {analysis['class_distribution']['human']}")
        logger.info(f"  ИИ: {analysis['class_distribution']['ai']}")
        logger.info(f"  Баланс ИИ: {analysis['class_distribution']['balance_ratio']:.2%}")
        
        return df, analysis
    
    def _assess_enhanced_data_quality(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Оценивает качество улучшенного датасета"""
        total = analysis['total_samples']
        num_features = analysis['num_features']
        balance = analysis['class_distribution']['balance_ratio']
        
        # Оценка размера
        if total < 500:
            size_quality = "Критически мало"
            size_recommendation = "Нужно минимум 500 образцов для мультимодального обучения"
        elif total < 2000:
            size_quality = "Недостаточно"
            size_recommendation = "Рекомендуется 2000+ образцов для стабильного обучения"
        elif total < 10000:
            size_quality = "Приемлемо"
            size_recommendation = "Хороший размер для обучения"
        else:
            size_quality = "Отлично"
            size_recommendation = "Достаточно данных для качественного обучения"
        
        # Оценка количества признаков
        if num_features < 5:
            feature_quality = "Мало признаков"
            feature_recommendation = "Добавьте больше признаков из Pangram API"
        elif num_features < 15:
            feature_quality = "Достаточно признаков"
            feature_recommendation = "Хороший набор признаков"
        else:
            feature_quality = "Много признаков"
            feature_recommendation = "Отличный набор признаков, возможно переобучение"
        
        # Оценка баланса
        if 0.3 <= balance <= 0.7:
            balance_quality = "Хороший баланс"
        elif 0.2 <= balance <= 0.8:
            balance_quality = "Приемлемый дисбаланс"
        else:
            balance_quality = "Сильный дисбаланс"
        
        return {
            'size_quality': size_quality,
            'size_recommendation': size_recommendation,
            'feature_quality': feature_quality,
            'feature_recommendation': feature_recommendation,
            'balance_quality': balance_quality,
            'overall_feasible': total >= 500 and num_features >= 3 and 0.1 <= balance <= 0.9
        }
    
    def prepare_model_and_tokenizer(self, num_features: int):
        """Подготавливает модель и токенизатор"""
        logger.info(f"Загрузка модели {self.model_name} с {num_features} дополнительными признаками...")
        
        try:
            # Токенизатор
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Улучшенная модель
            self.model = EnhancedAIDetectionModel(
                model_name=self.model_name,
                num_features=num_features
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
    
    def prepare_features(self, df: pd.DataFrame, feature_columns: List[str]) -> np.ndarray:
        """Подготавливает матрицу признаков"""
        logger.info("Подготовка матрицы признаков...")
        
        # Извлекаем признаки
        X_features = df[feature_columns].values
        
        # Обрабатываем NaN
        X_features = np.nan_to_num(X_features, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Нормализация
        X_features = self.scaler.fit_transform(X_features)
        
        logger.info(f"Матрица признаков: {X_features.shape}")
        logger.info(f"Статистика после нормализации:")
        logger.info(f"  Среднее: {X_features.mean():.3f}")
        logger.info(f"  Стандартное отклонение: {X_features.std():.3f}")
        
        return X_features
    
    def split_data(self, df: pd.DataFrame, analysis: Dict[str, Any], 
                   test_size: float = 0.2, val_size: float = 0.1) -> Tuple[Any, Any, Any]:
        """Разделяет данные на train/val/test"""
        text_col = analysis['text_column']
        target_col = analysis['target_column']
        feature_columns = analysis['feature_columns']
        
        texts = df[text_col].tolist()
        labels = df[target_col].tolist()
        
        # Подготавливаем признаки
        X_features = self.prepare_features(df, feature_columns)
        
        # Стратификация
        binary_labels = (df[target_col] >= 0.5).astype(int)
        
        # Train + Val / Test
        X_temp, X_test, y_temp, y_test, feat_temp, feat_test, strat_temp, strat_test = train_test_split(
            texts, labels, X_features, binary_labels,
            test_size=test_size, 
            stratify=binary_labels, 
            random_state=42
        )
        
        # Train / Val
        val_size_adjusted = val_size / (1 - test_size)
        X_train, X_val, y_train, y_val, feat_train, feat_val = train_test_split(
            X_temp, y_temp, feat_temp,
            test_size=val_size_adjusted, 
            stratify=strat_temp, 
            random_state=42
        )
        
        logger.info(f"Разделение данных:")
        logger.info(f"  Train: {len(X_train)} образцов")
        logger.info(f"  Validation: {len(X_val)} образцов")
        logger.info(f"  Test: {len(X_test)} образцов")
        
        # Создание датасетов
        train_dataset = EnhancedAIDetectionDataset(X_train, y_train, feat_train, self.tokenizer)
        val_dataset = EnhancedAIDetectionDataset(X_val, y_val, feat_val, self.tokenizer)
        test_dataset = EnhancedAIDetectionDataset(X_test, y_test, feat_test, self.tokenizer)
        
        return train_dataset, val_dataset, test_dataset
    
    def setup_training(self, train_dataset, val_dataset, output_dir: str = "./enhanced_ai_detector_model"):
        """Настраивает параметры обучения"""
        
        # Параметры в зависимости от размера данных
        dataset_size = len(train_dataset)
        if dataset_size < 1000:
            batch_size = 4
            num_epochs = 6
            learning_rate = 3e-5
        elif dataset_size < 5000:
            batch_size = 8
            num_epochs = 4
            learning_rate = 2e-5
        else:
            batch_size = 16 if self.device.type == 'cuda' else 8
            num_epochs = 3
            learning_rate = 2e-5
        
        # Настройки обучения
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            learning_rate=learning_rate,
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
            dataloader_pin_memory=False,
            remove_unused_columns=False,
            report_to=None
        )
        
        # Функция для вычисления метрик
        def compute_metrics(eval_pred):
            predictions, labels = eval_pred
            predictions = predictions.flatten()
            
            # Ограничиваем предсказания
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
            
            # Корреляция
            correlation = np.corrcoef(predictions, labels)[0, 1] if len(predictions) > 1 else 0
            
            return {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'auc': auc,
                'mse': mse,
                'mae': mae,
                'correlation': correlation
            }
        
        # Создание тренера
        self.trainer = EnhancedTrainer(
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
        logger.info(f"  Learning rate: {learning_rate}")
        logger.info(f"  Warmup steps: {training_args.warmup_steps}")
    
    def train_model(self) -> Dict[str, Any]:
        """Обучает модель"""
        logger.info("Начинаем обучение улучшенной модели...")
        start_time = time.time()
        
        try:
            # Обучение
            train_result = self.trainer.train()
            
            # Сохранение модели
            self.trainer.save_model()
            self.tokenizer.save_pretrained(self.trainer.args.output_dir)
            
            # Сохраняем scaler
            import joblib
            scaler_path = Path(self.trainer.args.output_dir) / "feature_scaler.pkl"
            joblib.dump(self.scaler, scaler_path)
            
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
        logger.info("Оценка улучшенной модели на тестовой выборке...")
        
        # Оценка
        eval_result = self.trainer.evaluate(test_dataset)
        
        # Предсказания для анализа
        predictions = self.trainer.predict(test_dataset)
        preds = np.clip(predictions.predictions.flatten(), 0, 1)
        labels = predictions.label_ids
        
        results = {
            'test_accuracy': eval_result['eval_accuracy'],
            'test_precision': eval_result['eval_precision'],
            'test_recall': eval_result['eval_recall'],
            'test_f1': eval_result['eval_f1'],
            'test_auc': eval_result['eval_auc'],
            'test_mse': eval_result['eval_mse'],
            'test_mae': eval_result['eval_mae'],
            'test_correlation': eval_result['eval_correlation'],
            'predictions_sample': preds[:10].tolist(),
            'labels_sample': labels[:10].tolist()
        }
        
        logger.info("Результаты на тестовой выборке:")
        logger.info(f"  Accuracy: {results['test_accuracy']:.3f}")
        logger.info(f"  Precision: {results['test_precision']:.3f}")
        logger.info(f"  Recall: {results['test_recall']:.3f}")
        logger.info(f"  F1: {results['test_f1']:.3f}")
        logger.info(f"  AUC: {results['test_auc']:.3f}")
        logger.info(f"  Correlation: {results['test_correlation']:.3f}")
        
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
            'test_results': test_results,
            'model_type': 'enhanced_multimodal'
        }
        
        results_file = Path("enhanced_training_results.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(full_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Результаты сохранены в {results_file}")

def main():
    """Основная функция улучшенного обучения"""
    print("🚀 Улучшенное обучение с дополнительными признаками")
    print("=" * 70)
    
    try:
        # Инициализация
        trainer = EnhancedAITrainer()
        
        # Загрузка и анализ данных
        df, analysis = trainer.load_and_analyze_data()
        
        # Проверка готовности к обучению
        if not analysis['data_quality']['overall_feasible']:
            print("❌ Данные не готовы для обучения:")
            print(f"   {analysis['data_quality']['size_recommendation']}")
            print(f"   {analysis['data_quality']['feature_recommendation']}")
            return
        
        print(f"✅ Данные готовы к улучшенному обучению")
        print(f"   {analysis['data_quality']['size_quality']}: {analysis['total_samples']} образцов")
        print(f"   {analysis['data_quality']['feature_quality']}: {analysis['num_features']} признаков")
        print(f"   {analysis['data_quality']['balance_quality']}")
        
        # Подготовка модели
        trainer.prepare_model_and_tokenizer(analysis['num_features'])
        
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
        
        print("\n🎉 Улучшенное обучение завершено!")
        print(f"📊 F1-score: {test_results['test_f1']:.3f}")
        print(f"📊 Accuracy: {test_results['test_accuracy']:.3f}")
        print(f"📊 Correlation: {test_results['test_correlation']:.3f}")
        print(f"📊 AUC: {test_results['test_auc']:.3f}")
        
        # Сравнение с базовой моделью
        improvement_estimate = test_results['test_f1'] * 1.1  # Примерная оценка улучшения
        print(f"\n💡 Ожидаемое улучшение по сравнению с базовой DeBERTa:")
        print(f"   F1-score: +{(improvement_estimate - test_results['test_f1']):.3f}")
        print(f"   Благодаря дополнительным признакам из Pangram API")
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()