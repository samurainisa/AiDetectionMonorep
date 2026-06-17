"""
Улучшенный извлечение признаков из текста
Удалены избыточные признаки, добавлены эффективные для детекции ИИ
"""
import re
import string
import statistics
import numpy as np
from collections import Counter
from typing import Dict, List, Optional
import math

# Попытка импорта дополнительных библиотек
try:
    import textstat
    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False

try:
    import nltk
    NLTK_AVAILABLE = True
    # Проверяем наличие нужных данных
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('punkt_tab', quiet=True)
        except:
            NLTK_AVAILABLE = False
except ImportError:
    NLTK_AVAILABLE = False

class TextFeatureExtractor:
    """Извлекает оптимизированные признаки для детекции ИИ-текстов"""
    
    def __init__(self):
        self.russian_stopwords = {
            'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так',
            'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было',
            'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг',
            'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж',
            'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть',
            'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам', 'чтоб', 'без', 'будто', 'чего',
            'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 'тогда', 'кто', 'этот', 'того', 'потому', 'этого',
            'какой', 'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее', 'сейчас',
            'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при', 'наконец', 'два', 'об', 'другой', 'хоть',
            'после', 'над', 'больше', 'тот', 'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много',
            'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой', 'перед', 'иногда', 'лучше', 'чуть',
            'том', 'нельзя', 'такой', 'им', 'более', 'всегда', 'конечно', 'всю', 'между'
        }
    
    def extract_features(self, text: str) -> Dict[str, float]:
        """Извлекает оптимизированный набор признаков"""
        if not text or not text.strip():
            return self._get_empty_features()
        
        # Базовая токенизация
        sentences = self._tokenize_sentences(text)
        words = self._tokenize_words(text.lower())
        
        features = {}
        
        # === БАЗОВЫЕ СТАТИСТИЧЕСКИЕ ПРИЗНАКИ ===
        features.update(self._extract_basic_stats(text, words, sentences))
        
        # === НОВЫЕ ЭФФЕКТИВНЫЕ ПРИЗНАКИ ДЛЯ ДЕТЕКЦИИ ИИ ===
        features.update(self._extract_burstiness(sentences))
        features.update(self._extract_mtld(words))
        features.update(self._extract_ngram_uniqueness(words))
        features.update(self._extract_hapax_ratio(words))
        features.update(self._extract_pronoun_bias(words))
        features.update(self._extract_perplexity_proxy(words))
        
        # === ОСТАВЛЕННЫЕ ПОЛЕЗНЫЕ ПРИЗНАКИ ===
        features.update(self._extract_readability_single(text))
        features.update(self._extract_linguistic_diversity(words))
        
        return features
    
    def _get_empty_features(self) -> Dict[str, float]:
        """Возвращает нулевые значения для пустого текста"""
        return {
            # Базовые
            'word_count': 0, 'sentence_count': 0, 'avg_sentence_length': 0,
            'punctuation_density': 0, 'uppercase_ratio': 0,
            # Новые эффективные
            'burstiness': 0, 'mtld_diversity': 0, 'bigram_uniqueness': 0, 'trigram_uniqueness': 0,
            'hapax_ratio': 0, 'pronoun_bias_first_person': 0, 'lexical_predictability': 0,
            # Оставленные полезные
            'russian_readability': 0, 'type_token_ratio': 0
        }
    
    def _tokenize_sentences(self, text: str) -> List[str]:
        """Токенизация предложений"""
        if NLTK_AVAILABLE:
            try:
                return nltk.sent_tokenize(text)
            except:
                pass
        # Fallback
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _tokenize_words(self, text: str) -> List[str]:
        """Токенизация слов"""
        return re.findall(r'\b\w+\b', text)
    
    def _extract_basic_stats(self, text: str, words: List[str], sentences: List[str]) -> Dict[str, float]:
        """Базовые статистические признаки (оптимизированные)"""
        word_count = len(words)
        sentence_count = len(sentences)
        
        # Только самые информативные базовые метрики
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        # Punctuation density с обработкой выбросов
        raw_punctuation_density = sum(1 for c in text if c in string.punctuation) / len(text) if text else 0
        # Ограничиваем максимальное значение чтобы избежать выбросов от формул/кода
        punctuation_density = min(0.15, raw_punctuation_density)  # 15% максимум
        
        uppercase_ratio = sum(1 for c in text if c.isupper()) / len(text) if text else 0
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'avg_sentence_length': avg_sentence_length,
            'punctuation_density': punctuation_density,
            'uppercase_ratio': uppercase_ratio
        }
    
    def _extract_burstiness(self, sentences: List[str]) -> Dict[str, float]:
        """Burstiness (σ/μ длины предложений) - ключевой признак для детекции ИИ"""
        if len(sentences) < 2:
            return {'burstiness': 0.0}
        
        # Длины предложений в словах
        sent_lengths = [len(self._tokenize_words(sent)) for sent in sentences]
        
        mean_length = np.mean(sent_lengths)
        std_length = np.std(sent_lengths)
        
        burstiness = std_length / mean_length if mean_length > 0 else 0
        
        return {'burstiness': burstiness}
    
    def _extract_mtld(self, words: List[str], threshold: float = 0.50) -> Dict[str, float]:
        """Measure of Textual Lexical Diversity (MTLD) - более стабильная мера разнообразия"""
        if len(words) < 50:
            # Для коротких текстов возвращаем простую метрику разнообразия
            unique_ratio = len(set(words)) / len(words) if words else 0
            # Масштабируем к диапазону MTLD (40-120 → 0.33-1.0)
            return {'mtld_diversity': min(1.0, unique_ratio * 1.2)}
        
        def calculate_mtld_forward(tokens, threshold):
            """MTLD прямой проход с правильным алгоритмом"""
            segments = []
            current_segment = []
            
            for token in tokens:
                current_segment.append(token)
                ttr = len(set(current_segment)) / len(current_segment)
                
                if ttr <= threshold:
                    segments.append(len(current_segment))
                    current_segment = []
            
            # Добавляем незавершенный сегмент с экстраполяцией
            if current_segment:
                ttr = len(set(current_segment)) / len(current_segment)
                if ttr > threshold:
                    # Правильная экстраполяция: оцениваем сколько еще слов нужно до порога
                    # Формула: factor = (ttr - threshold) / (1.0 - threshold)
                    factor = (ttr - threshold) / (1.0 - threshold) if ttr > threshold else 1.0
                    extrapolated_length = len(current_segment) / factor
                    segments.append(extrapolated_length)
                else:
                    segments.append(len(current_segment))
            
            return segments
        
        # Прямой и обратный проходы
        forward_segments = calculate_mtld_forward(words, threshold)
        backward_segments = calculate_mtld_forward(words[::-1], threshold)
        
        # Средняя длина сегмента = MTLD
        all_segments = forward_segments + backward_segments
        raw_mtld = np.mean(all_segments) if all_segments else 50.0
        
        # Нормализуем к диапазону 0-1: типичные значения MTLD 30-120
        # 30 = низкое разнообразие (0.0), 120 = высокое разнообразие (1.0)
        normalized_mtld = max(0.0, min(1.0, (raw_mtld - 30.0) / 90.0))
        
        return {'mtld_diversity': normalized_mtld}
    
    def _extract_ngram_uniqueness(self, words: List[str]) -> Dict[str, float]:
        """Уникальность биграмм и триграмм - детектирует повторяющиеся паттерны ИИ"""
        def ngram_uniqueness(tokens: List[str], n: int) -> float:
            if len(tokens) < n:
                return 1.0
            
            ngrams = [' '.join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]
            if not ngrams:
                return 0.0
            
            # Для коротких текстов (< 300 слов) используем модифицированную метрику
            if len(tokens) < 300:
                # Считаем повторяющиеся n-граммы
                ngram_counts = Counter(ngrams)
                repeated_ngrams = sum(1 for count in ngram_counts.values() if count > 1)
                total_ngrams = len(ngrams)
                # Возвращаем долю уникальных (не повторяющихся) n-грамм
                return (total_ngrams - repeated_ngrams) / total_ngrams
            else:
                # Для длинных текстов используем стандартную метрику
                return len(set(ngrams)) / len(ngrams)
        
        return {
            'bigram_uniqueness': ngram_uniqueness(words, 2),
            'trigram_uniqueness': ngram_uniqueness(words, 3)
        }
    
    def _extract_hapax_ratio(self, words: List[str]) -> Dict[str, float]:
        """Hapax ratio - доля слов, встречающихся только один раз"""
        if not words:
            return {'hapax_ratio': 0.0}
        
        word_counts = Counter(words)
        hapax_count = sum(1 for count in word_counts.values() if count == 1)
        hapax_ratio = hapax_count / len(words)
        
        return {'hapax_ratio': hapax_ratio}
    
    def _extract_pronoun_bias(self, words: List[str]) -> Dict[str, float]:
        """Bias первого лица - ИИ редко использует я/мы"""
        if not words:
            return {'pronoun_bias_first_person': 0.0}
        
        first_person_pronouns = {'я', 'мы', 'меня', 'мне', 'мной', 'мною', 'нас', 'нам', 'нами'}
        first_person_count = sum(1 for word in words if word in first_person_pronouns)
        
        return {'pronoun_bias_first_person': first_person_count / len(words)}
    
    def _extract_perplexity_proxy(self, words: List[str]) -> Dict[str, float]:
        """Метрика лексической предсказуемости на основе повторяемости паттернов"""
        if not words:
            return {'lexical_predictability': 0.0}
        
        word_counts = Counter(words)
        total_words = len(words)
        
        # 1. Компонент повторяемости слов
        # AI тексты часто повторяют ключевые термины
        repeated_words = sum(1 for count in word_counts.values() if count > 1)
        repetition_ratio = repeated_words / len(word_counts) if word_counts else 0
        
        # 2. Компонент концентрации частот
        # AI тексты имеют более равномерное использование слов
        freq_values = list(word_counts.values())
        if len(freq_values) > 1:
            # Доля слов с частотой 1 (hapax legomena)
            hapax_ratio = sum(1 for count in freq_values if count == 1) / len(freq_values)
            
            # Коэффициент вариации частот
            freq_mean = sum(freq_values) / len(freq_values)
            freq_std = (sum((f - freq_mean) ** 2 for f in freq_values) / len(freq_values)) ** 0.5
            cv = freq_std / freq_mean if freq_mean > 0 else 0
            
            # Нормализация CV через sigmoid для стабильности
            cv_normalized = 2.0 / (1.0 + math.exp(-cv)) - 1.0  # Sigmoid в диапазоне [0, 1]
        else:
            hapax_ratio = 1.0
            cv_normalized = 0.0
        
        # 3. Компонент длины слов
        # AI тексты часто используют более длинные, "научные" слова
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        # Нормализуем: 3-4 буквы = низкая предсказуемость, 7+ букв = высокая
        length_factor = min(1.0, max(0.0, (avg_word_length - 3.0) / 5.0))
        
        # Комбинированная метрика предсказуемости
        # Высокие значения = AI-подобный текст (предсказуемый)
        # Низкие значения = человеческий текст (непредсказуемый)
        lexical_predictability = (
            repetition_ratio * 0.4 +           # 40% - повторяемость слов
            (1.0 - hapax_ratio) * 0.3 +        # 30% - доля неуникальных слов
            (1.0 - cv_normalized) * 0.2 +      # 20% - равномерность распределения
            length_factor * 0.1                # 10% - длина слов
        )
        
        # Ограничиваем диапазон [0, 1]
        lexical_predictability = max(0.0, min(1.0, lexical_predictability))
        
        return {'lexical_predictability': lexical_predictability}
    
    def _extract_readability_single(self, text: str) -> Dict[str, float]:
        """Простая метрика читаемости для русского языка"""
        sentences = self._tokenize_sentences(text)
        words = self._tokenize_words(text)
        
        if not sentences or not words:
            return {'russian_readability': 0.0}
        
        # Русская формула читаемости (адаптированная)
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Упрощенная формула для русского: чем короче предложения и слова, тем читабельнее
        # Инвертируем шкалу: высокие значения = более читабельно
        readability = max(0, min(100, 100 - (avg_sentence_length * 2) - (avg_word_length * 8)))
        
        return {'russian_readability': readability}
    
    def _extract_linguistic_diversity(self, words: List[str]) -> Dict[str, float]:
        """Лингвистическое разнообразие (один показатель вместо нескольких)"""
        if not words:
            return {'type_token_ratio': 0.0}
        
        # Классический TTR как единственный показатель разнообразия
        return {'type_token_ratio': len(set(words)) / len(words)}
    
    def _count_syllables(self, word: str) -> int:
        """Простой подсчет слогов для русского языка"""
        vowels = 'аеёиоуыэюя'
        word = word.lower()
        count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                count += 1
            prev_was_vowel = is_vowel
        
        return max(1, count)  # Минимум 1 слог

def extract_pangram_features(pangram_response: dict) -> dict:
    """Извлекает дополнительные признаки из ответа Pangram API"""
    features = {}
    
    try:
        # Извлекаем предложения с высокой вероятностью ИИ
        if 'ai_sentences' in pangram_response and pangram_response['ai_sentences']:
            features['high_ai_sentences_count'] = len(pangram_response['ai_sentences'])
            # Средняя вероятность ИИ в предложениях
            ai_probs = [s.get('ai_likelihood', 0) for s in pangram_response['ai_sentences']]
            features['avg_ai_sentence_prob'] = sum(ai_probs) / len(ai_probs) if ai_probs else 0
        else:
            features['high_ai_sentences_count'] = 0
            features['avg_ai_sentence_prob'] = 0
        
        # Данные из sliding window
        if 'windows' in pangram_response and pangram_response['windows']:
            windows = pangram_response['windows']
            window_probs = []
            for window in windows:
                # V3: ai_assistance_score, Legacy: ai_likelihood
                prob = window.get('ai_likelihood')
                if prob is None:
                    prob = window.get('ai_assistance_score')
                if prob is not None:
                    try:
                        window_probs.append(float(prob))
                    except (TypeError, ValueError):
                        pass
            if window_probs:
                features['window_count'] = len(window_probs)
                features['max_window_prob'] = max(window_probs)
                features['min_window_prob'] = min(window_probs)
                features['window_prob_std'] = statistics.stdev(window_probs) if len(window_probs) > 1 else 0
                
                # Добавляем burstiness для окон с ограничением выбросов
                mean_prob = statistics.mean(window_probs)
                if mean_prob > 0.01:  # Минимальный порог для предотвращения деления на ~0
                    window_burstiness = statistics.stdev(window_probs) / mean_prob
                    # Ограничиваем экстремальные значения
                    window_burstiness = min(3.0, window_burstiness)
                else:
                    window_burstiness = 0
                features['window_burstiness'] = window_burstiness
            else:
                features['window_count'] = 0
                features['max_window_prob'] = 0
                features['min_window_prob'] = 0
                features['window_prob_std'] = 0
                features['window_burstiness'] = 0
        else:
            features['window_count'] = 0
            features['max_window_prob'] = 0
            features['min_window_prob'] = 0
            features['window_prob_std'] = 0
            features['window_burstiness'] = 0
            
    except Exception as e:
        print(f"Ошибка извлечения Pangram признаков: {e}")
        # Возвращаем нулевые значения при ошибке
        features.update({
            'high_ai_sentences_count': 0,
            'avg_ai_sentence_prob': 0,
            'window_count': 0,
            'max_window_prob': 0,
            'min_window_prob': 0,
            'window_prob_std': 0,
            'window_burstiness': 0
        })
    
    return features 
