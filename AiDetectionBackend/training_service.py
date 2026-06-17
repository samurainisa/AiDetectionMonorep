"""
Сервис для управления обучением и работой с локальным детектором ИИ
"""

import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Легковесная конфигурация, не требующая импорта ai_detector/torch."""
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
    confidence_threshold: float = 0.85

class TrainingService:
    """Сервис для автоматического обучения детектора"""
    
    def __init__(self, db_path: str, pangram_api_caller, ai_mode: str = "pangram_plus_ai"):
        # Flask создает базы данных в папке instance
        if not db_path.startswith('instance/'):
            self.db_path = os.path.join('instance', os.path.basename(db_path))
        else:
            self.db_path = db_path
        self.pangram_api_caller = pangram_api_caller
        self.ai_mode = (ai_mode or "pangram_plus_ai").strip().lower()
        self.local_ai_enabled = self.ai_mode == "pangram_plus_ai"
        self.local_detector = None
        self.hybrid_detector = None
        self.training_config = TrainingConfig()
        self.is_training = False
        self.training_thread = None
        self.auto_training_enabled = True
        self.check_interval = 3600  # Проверка каждый час
        
        if self.local_ai_enabled:
            # Инициализация детекторов
            self._initialize_detectors()
            
            # Запуск автоматического обучения
            if self.auto_training_enabled:
                self._start_auto_training()
        else:
            self.auto_training_enabled = False
            logger.info("Локальный AI отключен: используется только Pangram API")
            
    def _initialize_detectors(self):
        """Инициализирует детекторы"""
        if not self.local_ai_enabled:
            return
        try:
            # Импортируем тяжелые зависимости только в режиме pangram_plus_ai.
            from ai_detector import DetectorFactory, TrainingConfig as AIDetectorTrainingConfig
            self.training_config = AIDetectorTrainingConfig(
                model_name=self.training_config.model_name,
                max_length=self.training_config.max_length,
                batch_size=self.training_config.batch_size,
                learning_rate=self.training_config.learning_rate,
                num_epochs=self.training_config.num_epochs,
                warmup_steps=self.training_config.warmup_steps,
                weight_decay=self.training_config.weight_decay,
                early_stopping_patience=self.training_config.early_stopping_patience,
                min_samples_for_training=self.training_config.min_samples_for_training,
                validation_split=self.training_config.validation_split,
                test_split=self.training_config.test_split,
                confidence_threshold=self.training_config.confidence_threshold,
            )
            self.local_detector = DetectorFactory.create_local_detector(self.training_config)
            self.hybrid_detector = DetectorFactory.create_hybrid_detector(self.pangram_api_caller)
            logger.info("Детекторы успешно инициализированы")
        except Exception as e:
            logger.error(f"Ошибка инициализации детекторов: {e}")
            
    def _start_auto_training(self):
        """Запускает автоматическое обучение в отдельном потоке"""
        if not self.local_ai_enabled:
            return
        def auto_training_loop():
            while self.auto_training_enabled:
                try:
                    if self._should_retrain():
                        logger.info("Запуск автоматического переобучения")
                        self.train_model()
                except Exception as e:
                    logger.error(f"Ошибка в автоматическом обучении: {e}")
                    
                time.sleep(self.check_interval)
                
        self.training_thread = threading.Thread(target=auto_training_loop, daemon=True)
        self.training_thread.start()
        logger.info("Автоматическое обучение запущено")
        
    def _should_retrain(self) -> bool:
        """Проверяет, нужно ли переобучать модель"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM detection 
                    WHERE ai_likelihood IS NOT NULL 
                    AND created_at > datetime('now', '-24 hours')
                """)
                new_samples = cursor.fetchone()[0]
                
                # Переобучаем если накопилось достаточно новых образцов
                if new_samples >= 100:
                    return True
                    
                # Или если прошло много времени с последнего обучения
                if self.local_detector and self.local_detector.metrics.training_history:
                    last_training = self.local_detector.metrics.training_history[-1]
                    last_training_date = datetime.fromisoformat(last_training['timestamp'])
                    if datetime.now() - last_training_date > timedelta(days=7):
                        return True
                        
                return False
                
        except Exception as e:
            logger.error(f"Ошибка проверки необходимости переобучения: {e}")
            return False
            
    def train_model(self, force: bool = False) -> Dict[str, Any]:
        """Обучает локальную модель"""
        if not self.local_ai_enabled:
            return {'error': 'Локальный AI отключен (режим pangram_only)'}
        if self.is_training and not force:
            return {'error': 'Обучение уже выполняется'}
            
        self.is_training = True
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                texts, labels = self.local_detector.prepare_training_data(conn)
                
                if len(texts) < self.training_config.min_samples_for_training:
                    return {
                        'error': f'Недостаточно данных для обучения. Нужно минимум {self.training_config.min_samples_for_training}, доступно {len(texts)}'
                    }
                    
                training_metrics = self.local_detector.train(texts, labels)
                
                # Обновляем гибридный детектор
                self.hybrid_detector.local_detector = self.local_detector
                
                logger.info(f"Обучение завершено. Корреляция: {training_metrics['correlation_with_teacher']:.3f}")
                
                return {
                    'success': True,
                    'metrics': training_metrics,
                    'samples_used': len(texts),
                    'model_activated': training_metrics['correlation_with_teacher'] >= self.training_config.confidence_threshold
                }
                
        except Exception as e:
            logger.error(f"Ошибка обучения модели: {e}")
            return {'error': str(e)}
        finally:
            self.is_training = False
            
    def predict_text(self, text: str, use_hybrid: bool = True) -> Dict[str, Any]:
        """Предсказание для текста"""
        try:
            if not self.local_ai_enabled:
                api_response = self.pangram_api_caller(text)
                ai_probability = float(api_response.get('ai_likelihood', 0.5))
                confidence = 0.9
                prediction_source = 'pangram_only_mode'
                processing_time = 0.5
                model_version = None
            elif use_hybrid and self.hybrid_detector:
                result = self.hybrid_detector.predict(text)
                ai_probability = result.ai_probability
                confidence = result.confidence
                prediction_source = result.prediction_source
                processing_time = result.processing_time
                model_version = result.model_version
            elif self.local_detector and self.local_detector.is_trained:
                result = self.local_detector.predict(text)
                ai_probability = result.ai_probability
                confidence = result.confidence
                prediction_source = result.prediction_source
                processing_time = result.processing_time
                model_version = result.model_version
            else:
                # Fallback на Pangram API
                api_response = self.pangram_api_caller(text)
                ai_probability = float(api_response.get('ai_likelihood', 0.5))
                confidence = 0.9
                prediction_source = 'pangram_fallback'
                processing_time = 0.5
                model_version = None
                
            return {
                'ai_probability': ai_probability,
                'confidence': confidence,
                'prediction_source': prediction_source,
                'processing_time': processing_time,
                'model_version': model_version,
                'prediction': self._get_prediction_label(ai_probability)
            }
            
        except Exception as e:
            logger.error(f"Ошибка предсказания: {e}")
            return {'error': str(e)}
            
    def _get_prediction_label(self, ai_probability: float) -> str:
        """Преобразует вероятность в текстовую метку"""
        if ai_probability >= 0.8:
            return "Очень высокая вероятность ИИ"
        elif ai_probability >= 0.6:
            return "Высокая вероятность ИИ"
        elif ai_probability >= 0.4:
            return "Умеренная вероятность ИИ"
        elif ai_probability >= 0.2:
            return "Низкая вероятность ИИ"
        else:
            return "Человеческий текст"
            
    def get_training_status(self) -> Dict[str, Any]:
        """Возвращает статус обучения"""
        model_info = {}
        if self.local_detector:
            model_info = self.local_detector.get_model_info()
            
        return {
            'is_training': self.is_training,
            'ai_mode': self.ai_mode,
            'local_ai_enabled': self.local_ai_enabled,
            'auto_training_enabled': self.auto_training_enabled,
            'model_info': model_info,
            'training_config': {
                'min_samples': self.training_config.min_samples_for_training,
                'confidence_threshold': self.training_config.confidence_threshold,
                'model_name': self.training_config.model_name
            }
        }
        
    def get_dataset_stats(self) -> Dict[str, Any]:
        """Возвращает статистику датасета"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Общее количество образцов
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM detection 
                    WHERE ai_likelihood IS NOT NULL
                """)
                total_samples = cursor.fetchone()[0]
                
                # Распределение по вероятностям ИИ
                cursor = conn.execute("""
                    SELECT 
                        CASE 
                            WHEN ai_likelihood >= 0.8 THEN 'high_ai'
                            WHEN ai_likelihood >= 0.6 THEN 'medium_ai'
                            WHEN ai_likelihood >= 0.4 THEN 'mixed'
                            WHEN ai_likelihood >= 0.2 THEN 'medium_human'
                            ELSE 'high_human'
                        END as category,
                        COUNT(*) as count
                    FROM detection 
                    WHERE ai_likelihood IS NOT NULL
                    GROUP BY category
                """)
                distribution = dict(cursor.fetchall())
                
                # Образцы за последний месяц
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM detection 
                    WHERE ai_likelihood IS NOT NULL 
                    AND created_at > date('now', '-30 days')
                """)
                recent_samples = cursor.fetchone()[0]
                
                return {
                    'total_samples': total_samples,
                    'distribution': distribution,
                    'recent_samples_30d': recent_samples,
                    'ready_for_training': total_samples >= self.training_config.min_samples_for_training
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики датасета: {e}")
            return {'error': str(e)}
            
    def export_dataset(self, output_path: str, format: str = 'json') -> Dict[str, Any]:
        """Экспортирует датасет для исследований"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        id,
                        filename,
                        extracted_text,
                        ai_likelihood,
                        prediction,
                        created_at,
                        file_type
                    FROM detection 
                    WHERE ai_likelihood IS NOT NULL
                    ORDER BY created_at DESC
                """)
                
                data = []
                for row in cursor.fetchall():
                    data.append({
                        'id': row[0],
                        'filename': row[1],
                        'text': row[2],
                        'ai_likelihood': row[3],
                        'prediction': row[4],
                        'created_at': row[5],
                        'file_type': row[6]
                    })
                    
                output_file = Path(output_path)
                
                if format == 'json':
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                elif format == 'csv':
                    import pandas as pd
                    df = pd.DataFrame(data)
                    df.to_csv(output_file, index=False, encoding='utf-8')
                else:
                    return {'error': f'Неподдерживаемый формат: {format}'}
                    
                return {
                    'success': True,
                    'exported_samples': len(data),
                    'output_file': str(output_file),
                    'format': format
                }
                
        except Exception as e:
            logger.error(f"Ошибка экспорта датасета: {e}")
            return {'error': str(e)}
            
    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет конфигурацию обучения"""
        try:
            # Обновляем только разрешенные параметры
            allowed_params = [
                'batch_size', 'learning_rate', 'num_epochs', 
                'min_samples_for_training', 'confidence_threshold'
            ]
            
            updated = {}
            for param in allowed_params:
                if param in new_config:
                    setattr(self.training_config, param, new_config[param])
                    updated[param] = new_config[param]
                    
            if updated:
                logger.info(f"Обновлена конфигурация: {updated}")
                
            return {
                'success': True,
                'updated_params': updated,
                'current_config': {
                    param: getattr(self.training_config, param) 
                    for param in allowed_params
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка обновления конфигурации: {e}")
            return {'error': str(e)}
            
    def stop_auto_training(self):
        """Останавливает автоматическое обучение"""
        self.auto_training_enabled = False
        if self.training_thread:
            self.training_thread.join(timeout=5)
        logger.info("Автоматическое обучение остановлено")
        
    def get_training_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Возвращает логи обучения"""
        if self.local_detector and self.local_detector.metrics.training_history:
            return self.local_detector.metrics.training_history[-limit:]
        return []

# Глобальный экземпляр сервиса
training_service: Optional[TrainingService] = None

def initialize_training_service(db_path: str, pangram_api_caller):
    """Инициализирует глобальный сервис обучения"""
    global training_service
    ai_mode = os.getenv("AI_MODE", "pangram_plus_ai")
    training_service = TrainingService(db_path, pangram_api_caller, ai_mode=ai_mode)
    return training_service

def get_training_service() -> Optional[TrainingService]:
    """Возвращает глобальный сервис обучения"""
    return training_service 