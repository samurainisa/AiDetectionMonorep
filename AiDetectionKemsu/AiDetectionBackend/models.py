from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
import json
import hashlib

class Role(Enum):
    STUDENT = "student"
    TEACHER = "teacher" 
    ADMIN = "admin"
    DEVELOPER = "developer"

class MatchType(Enum):
    EXACT = "exact"
    NEAR_EXACT = "near_exact"
    PARAPHRASE = "paraphrase"
    SEMANTIC = "semantic"

class DocumentCategory(Enum):
    COURSEWORK = "coursework"
    ESSAY = "essay"
    REPORT = "report"
    THESIS = "thesis"
    HOMEWORK = "homework"
    OTHER = "other"

class User:
    def __init__(self, id: int, email: str, first_name: str, last_name: str, 
                 role: Role, group_id: Optional[int] = None, student_id: Optional[str] = None):
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.group_id = group_id
        self.student_id = student_id
        self.is_active = True
        self.created_at = datetime.now()
        self.last_login: Optional[datetime] = None
    
    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    def is_student(self) -> bool:
        return self.role == Role.STUDENT
    
    def is_teacher(self) -> bool:
        return self.role == Role.TEACHER
    
    def can_view_analytics(self) -> bool:
        return self.role in [Role.TEACHER, Role.ADMIN]

class Group:
    def __init__(self, id: int, name: str, course_code: str, academic_year: str):
        self.id = id
        self.name = name
        self.course_code = course_code
        self.academic_year = academic_year
        self.semester: Optional[int] = None
        self.faculty: Optional[str] = None
        self.students: List[User] = []
        self.created_at = datetime.now()
    
    def add_student(self, student: User):
        if student.is_student():
            self.students.append(student)
            student.group_id = self.id
    
    def get_student_count(self) -> int:
        return len(self.students)
    
    def get_active_students(self) -> List[User]:
        return [s for s in self.students if s.is_active]

class AIDetection:
    def __init__(self, user_id: int, filename: str, file_type: str, 
                 text_length: int, extracted_text: str):
        self.id: Optional[int] = None
        self.user_id = user_id
        self.filename = filename
        self.original_filename = filename
        self.file_type = file_type
        self.file_size: Optional[int] = None
        self.file_hash: Optional[str] = None
        self.text_length = text_length
        self.extracted_text = extracted_text
        
        # AI детекция результаты
        self.api_endpoint: Optional[str] = None
        self.ai_likelihood: Optional[float] = None
        self.max_ai_likelihood: Optional[float] = None
        self.avg_ai_likelihood: Optional[float] = None
        self.prediction: Optional[str] = None
        self.fraction_ai_content: Optional[float] = None
        self.full_response: Optional[Dict[str, Any]] = None
        
        # Расширенные признаки (статистические)
        self.word_count: Optional[int] = None
        self.sentence_count: Optional[int] = None
        self.paragraph_count: Optional[int] = None
        self.avg_word_length: Optional[float] = None
        self.avg_sentence_length: Optional[float] = None
        self.sentence_length_variance: Optional[float] = None
        self.punctuation_density: Optional[float] = None
        self.uppercase_ratio: Optional[float] = None
        
        # Признаки читаемости
        self.flesch_reading_ease: Optional[float] = None
        self.flesch_kincaid_grade: Optional[float] = None
        self.automated_readability_index: Optional[float] = None
        self.coleman_liau_index: Optional[float] = None
        self.gunning_fog: Optional[float] = None
        self.smog_index: Optional[float] = None
        self.reading_time: Optional[float] = None
        
        # Лингвистические признаки
        self.type_token_ratio: Optional[float] = None
        self.hapax_ratio: Optional[float] = None
        self.academic_density: Optional[float] = None
        self.modal_density: Optional[float] = None
        self.passive_density: Optional[float] = None
        
        # Дополнительные Pangram признаки
        self.pangram_window_variance: Optional[float] = None
        self.pangram_ai_sentences_count: Optional[int] = None
        
        # Метаданные
        self.document_category: Optional[DocumentCategory] = None
        self.assignment_name: Optional[str] = None
        self.subject: Optional[str] = None
        self.is_public = False
        
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def generate_file_hash(self) -> str:
        """Генерирует хеш файла для дедупликации"""
        content = f"{self.filename}_{self.text_length}_{self.extracted_text[:100]}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def set_pangram_response(self, response: Dict[str, Any], endpoint: str):
        """Сохраняет ответ от Pangram API"""
        self.api_endpoint = endpoint
        self.ai_likelihood = response.get('ai_likelihood')
        self.max_ai_likelihood = response.get('max_ai_likelihood')
        self.avg_ai_likelihood = response.get('avg_ai_likelihood')
        self.prediction = response.get('prediction')
        self.fraction_ai_content = response.get('fraction_ai_content')
        self.full_response = response
        
        # Дополнительные признаки для sliding window
        if 'windows' in response and response['windows']:
            windows = response['windows']
            window_scores = [w.get('ai_likelihood', 0) for w in windows if w.get('ai_likelihood')]
            if window_scores:
                import statistics
                self.pangram_window_variance = statistics.variance(window_scores) if len(window_scores) > 1 else 0.0
        
        # Подсчет AI предложений
        if 'ai_sentences' in response:
            self.pangram_ai_sentences_count = len(response['ai_sentences'])
        
        self.updated_at = datetime.now()
    
    def set_text_features(self, features: Dict[str, Any]):
        """Сохраняет извлеченные текстовые признаки"""
        # Статистические признаки
        self.word_count = features.get('word_count')
        self.sentence_count = features.get('sentence_count') 
        self.paragraph_count = features.get('paragraph_count')
        self.avg_word_length = features.get('avg_word_length')
        self.avg_sentence_length = features.get('avg_sentence_length')
        self.sentence_length_variance = features.get('sentence_length_variance')
        self.punctuation_density = features.get('punctuation_density')
        self.uppercase_ratio = features.get('uppercase_ratio')
        
        # Признаки читаемости
        self.flesch_reading_ease = features.get('flesch_reading_ease')
        self.flesch_kincaid_grade = features.get('flesch_kincaid_grade')
        self.automated_readability_index = features.get('automated_readability_index')
        self.coleman_liau_index = features.get('coleman_liau_index')
        self.gunning_fog = features.get('gunning_fog')
        self.smog_index = features.get('smog_index')
        self.reading_time = features.get('reading_time')
        
        # Лингвистические признаки
        self.type_token_ratio = features.get('type_token_ratio')
        self.hapax_ratio = features.get('hapax_ratio')
        self.academic_density = features.get('academic_density')
        self.modal_density = features.get('modal_density')
        self.passive_density = features.get('passive_density')
        
        self.updated_at = datetime.now()
    
    def is_high_ai_risk(self, threshold: float = 0.7) -> bool:
        """Проверяет высокий риск использования AI"""
        return self.ai_likelihood is not None and self.ai_likelihood > threshold
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'text_length': self.text_length,
            'ai_likelihood': self.ai_likelihood,
            'prediction': self.prediction,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        # Добавляем расширенные признаки если они есть
        extended_features = {
            'word_count': self.word_count,
            'sentence_count': self.sentence_count,
            'avg_word_length': self.avg_word_length,
            'flesch_reading_ease': self.flesch_reading_ease,
            'type_token_ratio': self.type_token_ratio,
            'academic_density': self.academic_density
        }
        
        # Добавляем только не-None значения
        for key, value in extended_features.items():
            if value is not None:
                result[key] = value
                
        return result

class TextFragment:
    def __init__(self, detection_id: int, fragment_text: str, 
                 start_position: int, end_position: int):
        self.id: Optional[int] = None
        self.detection_id = detection_id
        self.fragment_text = fragment_text
        self.start_position = start_position
        self.end_position = end_position
        self.word_count = len(fragment_text.split())
        self.fragment_hash = self.generate_hash()
        self.embedding_vector: Optional[List[float]] = None
        self.created_at = datetime.now()
    
    def generate_hash(self) -> str:
        """Генерирует хеш фрагмента"""
        return hashlib.md5(self.fragment_text.encode()).hexdigest()
    
    def set_embedding(self, vector: List[float]):
        """Устанавливает векторное представление"""
        self.embedding_vector = vector
    
    def get_text_preview(self, max_length: int = 100) -> str:
        """Возвращает превью текста фрагмента"""
        if len(self.fragment_text) <= max_length:
            return self.fragment_text
        return self.fragment_text[:max_length] + "..."

class PlagiarismMatch:
    def __init__(self, source_detection_id: int, target_detection_id: int,
                 source_fragment_id: int, target_fragment_id: int,
                 similarity_score: float, match_type: MatchType):
        self.id: Optional[int] = None
        self.source_detection_id = source_detection_id
        self.target_detection_id = target_detection_id
        self.source_fragment_id = source_fragment_id
        self.target_fragment_id = target_fragment_id
        self.similarity_score = similarity_score
        self.match_type = match_type
        self.match_length: Optional[int] = None
        self.created_at = datetime.now()
    
    def is_significant(self, threshold: float = 0.8) -> bool:
        """Проверяет значимость совпадения"""
        return self.similarity_score >= threshold
    
    def get_similarity_percentage(self) -> int:
        """Возвращает процент схожести"""
        return int(self.similarity_score * 100)

class PlagiarismReport:
    def __init__(self, detection_id: int):
        self.id: Optional[int] = None
        self.detection_id = detection_id
        self.total_similarity_score: float = 0.0
        self.unique_matches_count: int = 0
        self.total_matched_words: int = 0
        self.matches: List[PlagiarismMatch] = []
        self.report_data: Optional[Dict[str, Any]] = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_match(self, match: PlagiarismMatch):
        """Добавляет совпадение в отчет"""
        self.matches.append(match)
        self.unique_matches_count += 1
        if match.match_length:
            self.total_matched_words += match.match_length
        self._update_total_similarity()
    
    def _update_total_similarity(self):
        """Обновляет общий показатель схожести"""
        if self.matches:
            self.total_similarity_score = max(m.similarity_score for m in self.matches)
        self.updated_at = datetime.now()
    
    def get_plagiarism_level(self) -> str:
        """Определяет уровень плагиата"""
        if self.total_similarity_score >= 0.8:
            return "Высокий"
        elif self.total_similarity_score >= 0.5:
            return "Средний"
        elif self.total_similarity_score >= 0.2:
            return "Низкий"
        else:
            return "Не обнаружен"
    
    def is_plagiarism_detected(self, threshold: float = 0.15) -> bool:
        """Проверяет обнаружение плагиата"""
        return self.total_similarity_score > threshold
    
    def generate_summary(self) -> Dict[str, Any]:
        """Генерирует краткий отчет"""
        return {
            'detection_id': self.detection_id,
            'plagiarism_level': self.get_plagiarism_level(),
            'similarity_score': self.total_similarity_score,
            'matches_count': self.unique_matches_count,
            'matched_words': self.total_matched_words,
            'is_plagiarism': self.is_plagiarism_detected(),
            'created_at': self.created_at.isoformat()
        }

class UserStatistics:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.total_documents: int = 0
        self.avg_ai_likelihood: float = 0.0
        self.high_ai_documents: int = 0
        self.plagiarism_cases: int = 0
        self.last_activity: Optional[datetime] = None
        self.subjects: List[str] = []
    
    def calculate_ai_risk_ratio(self) -> float:
        """Вычисляет долю документов с высоким AI риском"""
        if self.total_documents == 0:
            return 0.0
        return self.high_ai_documents / self.total_documents
    
    def get_activity_status(self) -> str:
        """Определяет статус активности пользователя"""
        if not self.last_activity:
            return "Неактивен"
        
        days_since_activity = (datetime.now() - self.last_activity).days
        if days_since_activity <= 7:
            return "Активен"
        elif days_since_activity <= 30:
            return "Умеренно активен"
        else:
            return "Малоактивен"

class GroupAnalytics:
    def __init__(self, group_id: int, group_name: str):
        self.group_id = group_id
        self.group_name = group_name
        self.students_count: int = 0
        self.total_documents: int = 0
        self.avg_ai_likelihood: float = 0.0
        self.high_ai_documents: int = 0
        self.plagiarism_cases: int = 0
        self.most_active_students: List[int] = []
        self.risk_students: List[int] = []  # студенты с высоким AI/плагиат риском
    
    def calculate_group_risk_score(self) -> float:
        """Вычисляет общий риск группы"""
        if self.total_documents == 0:
            return 0.0
        
        ai_risk = self.high_ai_documents / self.total_documents
        plagiarism_risk = self.plagiarism_cases / self.total_documents
        return (ai_risk + plagiarism_risk) / 2
    
    def get_risk_level(self) -> str:
        """Определяет уровень риска группы"""
        risk_score = self.calculate_group_risk_score()
        if risk_score >= 0.5:
            return "Высокий риск"
        elif risk_score >= 0.3:
            return "Средний риск"
        elif risk_score >= 0.1:
            return "Низкий риск"
        else:
            return "Минимальный риск"

# Фабричные методы для создания объектов
class ModelFactory:
    @staticmethod
    def create_student(email: str, first_name: str, last_name: str, 
                      student_id: str, group_id: int) -> User:
        return User(
            id=0,  # будет установлен при сохранении в БД
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=Role.STUDENT,
            group_id=group_id,
            student_id=student_id
        )
    
    @staticmethod
    def create_teacher(email: str, first_name: str, last_name: str, 
                      employee_id: str) -> User:
        return User(
            id=0,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=Role.TEACHER,
            student_id=employee_id
        )
    
    @staticmethod
    def create_detection_from_upload(user_id: int, filename: str, 
                                   file_type: str, extracted_text: str) -> AIDetection:
        detection = AIDetection(
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            text_length=len(extracted_text.split()),
            extracted_text=extracted_text
        )
        detection.file_hash = detection.generate_file_hash()
        return detection 