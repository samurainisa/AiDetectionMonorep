#!/usr/bin/env python3
"""
Улучшенный сборщик датасета с признаками из Pangram API
"""

import pandas as pd
import numpy as np
import requests
import json
import time
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import re
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import textstat
import nltk
from collections import Counter

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PangramResponse:
    """Структура ответа от Pangram API"""
    ai_likelihood: float
    prediction: str
    text: str
    max_ai_likelihood: Optional[float] = None
    avg_ai_likelihood: Optional[float] = None
    fraction_ai_content: Optional[float] = None
    ai_sentences: Optional[List[str]] = None
    windows: Optional[List[Dict]] = None

class TextFeatureExtractor:
    """Извлекает дополнительные признаки из текста"""
    
    def __init__(self):
        # Загружаем NLTK данные если нужно
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            try:
                nltk.download('punkt', quiet=True)
            except:
                pass
        
        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            try:
                nltk.download('punkt_tab', quiet=True)
            except:
                pass
        
        try:
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            try:
                nltk.download('averaged_perceptron_tagger', quiet=True)
            except:
                pass
    
    def extract_statistical_features(self, text: str) -> Dict[str, float]:
        """Извлекает статистические признаки текста"""
        try:
            sentences = nltk.sent_tokenize(text)
            words = nltk.word_tokenize(text)
        except:
            # Fallback без NLTK
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            words = text.split()
        
        # Базовая статистика
        word_count = len(words)
        sentence_count = len(sentences)
        char_count = len(text)
        
        # Средние значения
        avg_word_length = np.mean([len(word) for word in words]) if words else 0
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        # Вариативность
        try:
            sentence_lengths = [len(nltk.word_tokenize(sent)) for sent in sentences]
        except:
            sentence_lengths = [len(sent.split()) for sent in sentences]
        sentence_length_variance = np.var(sentence_lengths) if len(sentence_lengths) > 1 else 0
        
        # Пунктуация
        punctuation_count = sum(1 for char in text if char in '.,!?;:')
        punctuation_density = punctuation_count / char_count if char_count > 0 else 0
        
        # Заглавные буквы
        uppercase_count = sum(1 for char in text if char.isupper())
        uppercase_ratio = uppercase_count / char_count if char_count > 0 else 0
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'char_count': char_count,
            'avg_word_length': avg_word_length,
            'avg_sentence_length': avg_sentence_length,
            'sentence_length_variance': sentence_length_variance,
            'punctuation_density': punctuation_density,
            'uppercase_ratio': uppercase_ratio
        }
    
    def extract_readability_features(self, text: str) -> Dict[str, float]:
        """Извлекает показатели читаемости"""
        try:
            return {
                'flesch_reading_ease': textstat.flesch_reading_ease(text),
                'flesch_kincaid_grade': textstat.flesch_kincaid_grade(text),
                'automated_readability_index': textstat.automated_readability_index(text),
                'coleman_liau_index': textstat.coleman_liau_index(text),
                'gunning_fog': textstat.gunning_fog(text),
                'smog_index': textstat.smog_index(text),
                'reading_time': textstat.reading_time(text, ms_per_char=14.69)
            }
        except:
            # Если textstat не работает, возвращаем нули
            return {
                'flesch_reading_ease': 0.0,
                'flesch_kincaid_grade': 0.0,
                'automated_readability_index': 0.0,
                'coleman_liau_index': 0.0,
                'gunning_fog': 0.0,
                'smog_index': 0.0,
                'reading_time': 0.0
            }
    
    def extract_linguistic_features(self, text: str) -> Dict[str, float]:
        """Извлекает лингвистические признаки"""
        try:
            words = nltk.word_tokenize(text.lower())
            sentences = nltk.sent_tokenize(text)
        except:
            # Fallback без NLTK
            words = text.lower().split()
            sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        # Лексическое разнообразие
        unique_words = len(set(words))
        total_words = len(words)
        type_token_ratio = unique_words / total_words if total_words > 0 else 0
        
        # Hapax legomena (слова, встречающиеся только раз)
        word_freq = Counter(words)
        hapax_count = sum(1 for count in word_freq.values() if count == 1)
        hapax_ratio = hapax_count / total_words if total_words > 0 else 0
        
        # Академические маркеры
        academic_words = [
            'исследование', 'анализ', 'изучение', 'рассмотрение', 'определение',
            'установление', 'выявление', 'обнаружение', 'доказательство', 'подтверждение',
            'таким образом', 'следовательно', 'в результате', 'в заключение',
            'целью является', 'задачей является', 'необходимо отметить'
        ]
        
        text_lower = text.lower()
        academic_count = sum(1 for word in academic_words if word in text_lower)
        academic_density = academic_count / len(sentences) if sentences else 0
        
        # Модальные глаголы и неопределенность
        modal_words = ['может', 'мог', 'должен', 'следует', 'необходимо', 'возможно', 'вероятно']
        modal_count = sum(1 for word in modal_words if word in text_lower)
        modal_density = modal_count / total_words if total_words > 0 else 0
        
        # Пассивный залог (упрощенная эвристика)
        passive_markers = ['был', 'была', 'было', 'были', 'является', 'рассматривается', 'изучается']
        passive_count = sum(1 for marker in passive_markers if marker in text_lower)
        passive_density = passive_count / len(sentences) if sentences else 0
        
        return {
            'type_token_ratio': type_token_ratio,
            'hapax_ratio': hapax_ratio,
            'academic_density': academic_density,
            'modal_density': modal_density,
            'passive_density': passive_density
        }
    
    def extract_all_features(self, text: str) -> Dict[str, float]:
        """Извлекает все признаки"""
        features = {}
        features.update(self.extract_statistical_features(text))
        features.update(self.extract_readability_features(text))
        features.update(self.extract_linguistic_features(text))
        return features

class PangramAPIClient:
    """Клиент для работы с Pangram API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'x-api-key': api_key
        })
        
        # Лимиты API
        self.rate_limit_delay = 1.0  # секунд между запросами
        self.last_request_time = 0
    
    def _wait_for_rate_limit(self):
        """Ожидает для соблюдения лимитов API"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    def analyze_text(self, text: str, return_ai_sentences: bool = True) -> Optional[PangramResponse]:
        """Анализирует текст через стандартное API"""
        self._wait_for_rate_limit()
        
        try:
            response = self.session.post(
                'https://text.api.pangramlabs.com',
                json={
                    'text': text,
                    'return_ai_sentences': return_ai_sentences
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return PangramResponse(
                    ai_likelihood=data['ai_likelihood'],
                    prediction=data['prediction'],
                    text=data['text'],
                    ai_sentences=data.get('ai_sentences', [])
                )
            else:
                logger.warning(f"Pangram API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Pangram API request failed: {e}")
            return None
    
    def analyze_text_sliding_window(self, text: str, return_ai_sentences: bool = True) -> Optional[PangramResponse]:
        """Анализирует текст через sliding window API"""
        self._wait_for_rate_limit()
        
        try:
            response = self.session.post(
                'https://text-sliding.api.pangramlabs.com',
                json={
                    'text': text,
                    'return_ai_sentences': return_ai_sentences
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return PangramResponse(
                    ai_likelihood=data['ai_likelihood'],
                    prediction=data['prediction'],
                    text=data['text'],
                    max_ai_likelihood=data.get('max_ai_likelihood'),
                    avg_ai_likelihood=data.get('avg_ai_likelihood'),
                    fraction_ai_content=data.get('fraction_ai_content'),
                    windows=data.get('windows', []),
                    ai_sentences=data.get('ai_sentences', [])
                )
            else:
                logger.warning(f"Pangram sliding API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Pangram sliding API request failed: {e}")
            return None
    
    def analyze_batch(self, texts: List[str]) -> List[Optional[PangramResponse]]:
        """Анализирует несколько текстов через batch API"""
        self._wait_for_rate_limit()
        
        try:
            response = self.session.post(
                'https://text-batch.api.pangramlabs.com',
                json={'text': texts},
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data['responses']:
                    results.append(PangramResponse(
                        ai_likelihood=item['ai_likelihood'],
                        prediction=item['prediction'],
                        text=item['text']
                    ))
                return results
            else:
                logger.warning(f"Pangram batch API error {response.status_code}: {response.text}")
                return [None] * len(texts)
                
        except Exception as e:
            logger.error(f"Pangram batch API request failed: {e}")
            return [None] * len(texts)

class EnhancedDatasetCollector:
    """Улучшенный сборщик датасета с признаками из Pangram"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.pangram_client = PangramAPIClient(api_key) if api_key else None
        self.feature_extractor = TextFeatureExtractor()
        
    def process_single_text(self, text: str, use_sliding_window: bool = False) -> Dict[str, Any]:
        """Обрабатывает один текст и извлекает все признаки"""
        result = {
            'text': text,
            'char_count': len(text),
            'word_count': len(text.split())
        }
        
        # Извлекаем локальные признаки
        local_features = self.feature_extractor.extract_all_features(text)
        result.update(local_features)
        
        # Если есть API ключ, получаем данные от Pangram
        if self.pangram_client:
            # Выбираем API в зависимости от длины текста
            if len(text.split()) > 400 or use_sliding_window:
                pangram_response = self.pangram_client.analyze_text_sliding_window(text)
            else:
                pangram_response = self.pangram_client.analyze_text(text)
            
            if pangram_response:
                # Основные метрики
                result.update({
                    'pangram_ai_likelihood': pangram_response.ai_likelihood,
                    'pangram_prediction': pangram_response.prediction
                })
                
                # Sliding window метрики (если есть)
                if pangram_response.max_ai_likelihood is not None:
                    result.update({
                        'pangram_max_ai_likelihood': pangram_response.max_ai_likelihood,
                        'pangram_avg_ai_likelihood': pangram_response.avg_ai_likelihood,
                        'pangram_fraction_ai_content': pangram_response.fraction_ai_content,
                        'pangram_window_count': len(pangram_response.windows) if pangram_response.windows else 0
                    })
                    
                    # Дополнительные метрики из окон
                    if pangram_response.windows:
                        window_scores = [w['ai_likelihood'] for w in pangram_response.windows]
                        result.update({
                            'pangram_window_variance': np.var(window_scores),
                            'pangram_window_std': np.std(window_scores),
                            'pangram_window_range': max(window_scores) - min(window_scores)
                        })
                
                # AI предложения (если есть)
                if pangram_response.ai_sentences:
                    result.update({
                        'pangram_ai_sentences_count': len(pangram_response.ai_sentences),
                        'pangram_ai_sentences_ratio': len(pangram_response.ai_sentences) / result['sentence_count'] if result['sentence_count'] > 0 else 0,
                        'pangram_ai_sentences': '; '.join(pangram_response.ai_sentences[:3])  # Первые 3 предложения
                    })
            else:
                # Если API недоступно, заполняем нулями
                result.update({
                    'pangram_ai_likelihood': None,
                    'pangram_prediction': None
                })
        
        return result
    
    def process_dataset(self, input_file: str, output_file: str = None, 
                       use_sliding_window: bool = False, max_samples: int = None) -> pd.DataFrame:
        """Обрабатывает весь датасет"""
        
        # Загружаем исходный датасет
        if input_file.endswith('.csv'):
            df = pd.read_csv(input_file)
        elif input_file.endswith('.json'):
            df = pd.read_json(input_file)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {input_file}")
        
        logger.info(f"Загружен датасет: {len(df)} записей")
        
        # Ограничиваем количество для тестирования
        if max_samples and len(df) > max_samples:
            df = df.head(max_samples)
            logger.info(f"Ограничено до {max_samples} записей для тестирования")
        
        # Находим колонку с текстом
        text_column = None
        for col in df.columns:
            if 'text' in col.lower():
                text_column = col
                break
        
        if not text_column:
            raise ValueError("Не найдена колонка с текстом")
        
        logger.info(f"Используем колонку '{text_column}' как источник текста")
        
        # Обрабатываем каждый текст
        enhanced_data = []
        
        for idx, row in df.iterrows():
            text = row[text_column]
            if pd.isna(text) or len(str(text).strip()) < 50:
                continue
            
            logger.info(f"Обрабатываем запись {idx+1}/{len(df)}")
            
            try:
                enhanced_record = self.process_single_text(str(text), use_sliding_window)
                
                # Добавляем оригинальные данные
                for col in df.columns:
                    if col != text_column:
                        enhanced_record[f'original_{col}'] = row[col]
                
                enhanced_data.append(enhanced_record)
                
            except Exception as e:
                logger.error(f"Ошибка обработки записи {idx}: {e}")
                continue
        
        # Создаем новый датафрейм
        enhanced_df = pd.DataFrame(enhanced_data)
        
        # Сохраняем результат
        if output_file:
            if output_file.endswith('.csv'):
                enhanced_df.to_csv(output_file, index=False)
            elif output_file.endswith('.json'):
                enhanced_df.to_json(output_file, orient='records', indent=2)
            logger.info(f"Улучшенный датасет сохранен: {output_file}")
        
        logger.info(f"Обработка завершена. Получено {len(enhanced_df)} записей с {len(enhanced_df.columns)} признаками")
        
        return enhanced_df
    
    def analyze_feature_importance(self, df: pd.DataFrame, target_column: str = 'original_ai_likelihood'):
        """Анализирует важность признаков"""
        if target_column not in df.columns:
            logger.warning(f"Целевая колонка '{target_column}' не найдена")
            return
        
        # Выбираем только числовые признаки
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        feature_columns = [col for col in numeric_columns if col != target_column and not col.startswith('original_')]
        
        if len(feature_columns) == 0:
            logger.warning("Не найдено числовых признаков для анализа")
            return
        
        # Корреляция с целевой переменной
        correlations = []
        for col in feature_columns:
            try:
                corr = df[col].corr(df[target_column])
                if not pd.isna(corr):
                    correlations.append((col, abs(corr)))
            except:
                continue
        
        # Сортируем по важности
        correlations.sort(key=lambda x: x[1], reverse=True)
        
        logger.info("Топ-10 наиболее важных признаков:")
        for i, (feature, corr) in enumerate(correlations[:10]):
            logger.info(f"  {i+1:2d}. {feature:30s} | корреляция: {corr:.3f}")
        
        return correlations

def main():
    """Основная функция для тестирования"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Улучшенный сборщик датасета')
    parser.add_argument('input_file', help='Путь к исходному датасету')
    parser.add_argument('--output', help='Путь для сохранения улучшенного датасета')
    parser.add_argument('--api-key', help='API ключ Pangram')
    parser.add_argument('--sliding-window', action='store_true', help='Использовать sliding window API')
    parser.add_argument('--max-samples', type=int, help='Максимальное количество образцов для обработки')
    
    args = parser.parse_args()
    
    # Создаем сборщик
    collector = EnhancedDatasetCollector(args.api_key)
    
    # Определяем выходной файл
    if not args.output:
        input_path = Path(args.input_file)
        args.output = str(input_path.parent / f"enhanced_{input_path.name}")
    
    # Обрабатываем датасет
    enhanced_df = collector.process_dataset(
        args.input_file, 
        args.output,
        args.sliding_window,
        args.max_samples
    )
    
    # Анализируем важность признаков
    collector.analyze_feature_importance(enhanced_df)
    
    print(f"\n✅ Готово! Улучшенный датасет сохранен в {args.output}")
    print(f"📊 Признаков: {len(enhanced_df.columns)}")
    print(f"📝 Записей: {len(enhanced_df)}")

if __name__ == "__main__":
    main()