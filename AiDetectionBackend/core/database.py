"""
Модели базы данных и функции работы с БД
"""
import os
import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from sqlalchemy import text as sql_text

db = SQLAlchemy()

class Detection(db.Model):
    """Модель для хранения результатов детекции ИИ"""
    id = db.Column(db.Integer, primary_key=True)
    # Владелец детекции (пользователь). Допускается NULL для старых записей
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    text_length = db.Column(db.Integer, nullable=False)  # Количество слов
    char_count = db.Column(db.Integer, nullable=True)    # Количество символов
    extracted_text = db.Column(db.Text, nullable=False)
    api_endpoint = db.Column(db.String(50), nullable=False)
    ai_likelihood = db.Column(db.Float, nullable=True)
    max_ai_likelihood = db.Column(db.Float, nullable=True)
    avg_ai_likelihood = db.Column(db.Float, nullable=True)
    prediction = db.Column(db.Text, nullable=True)
    fraction_ai_content = db.Column(db.Float, nullable=True)
    full_response = db.Column(db.Text, nullable=False)
    
    # Расширенные признаки (статистические)
    word_count = db.Column(db.Integer, nullable=True)
    sentence_count = db.Column(db.Integer, nullable=True)
    paragraph_count = db.Column(db.Integer, nullable=True)
    avg_word_length = db.Column(db.Float, nullable=True)
    avg_sentence_length = db.Column(db.Float, nullable=True)
    sentence_length_variance = db.Column(db.Float, nullable=True)
    punctuation_density = db.Column(db.Float, nullable=True)
    uppercase_ratio = db.Column(db.Float, nullable=True)
    
    # Признаки читаемости (обновлено для русского языка)
    russian_readability = db.Column(db.Float, nullable=True)
    
    # Лингвистические признаки (оптимизированные)
    type_token_ratio = db.Column(db.Float, nullable=True)
    hapax_ratio = db.Column(db.Float, nullable=True)
    
    # Новые эффективные признаки для детекции ИИ
    burstiness = db.Column(db.Float, nullable=True)
    mtld_diversity = db.Column(db.Float, nullable=True)
    bigram_uniqueness = db.Column(db.Float, nullable=True)
    trigram_uniqueness = db.Column(db.Float, nullable=True)
    pronoun_bias_first_person = db.Column(db.Float, nullable=True)
    lexical_predictability = db.Column(db.Float, nullable=True)
    
    # Дополнительные Pangram признаки
    pangram_window_variance = db.Column(db.Float, nullable=True)
    pangram_ai_sentences_count = db.Column(db.Integer, nullable=True)
    pangram_window_burstiness = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PlagiarismCheck(db.Model):
    """Отдельная таблица для проверок на плагиат"""
    __tablename__ = 'plagiarism_checks'

    id = db.Column(db.Integer, primary_key=True)
    detection_id = db.Column(db.Integer, db.ForeignKey('detection.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    filename = db.Column(db.String(255), nullable=True)
    similarity_percentage = db.Column(db.Float, nullable=False)
    originality_percentage = db.Column(db.Float, nullable=False)
    plagiarism_level = db.Column(db.String(32), nullable=False)

    total_fragments = db.Column(db.Integer, nullable=False)
    matched_fragments = db.Column(db.Integer, nullable=False)

    matches_json = db.Column(db.Text, nullable=False)  # JSON список совпадений
    similar_documents_json = db.Column(db.Text, nullable=False)  # JSON список похожих документов

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class PlagiarismCorpusDoc(db.Model):
    """Документ в корпусе для антиплагиата"""
    __tablename__ = 'plagiarism_corpus'

    detection_id = db.Column(db.Integer, db.ForeignKey('detection.id'), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    text_length = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class PlagiarismFragment(db.Model):
    """Фрагменты текста (шинглы) для сравнения"""
    __tablename__ = 'text_fragments'

    id = db.Column(db.Integer, primary_key=True)
    detection_id = db.Column(db.Integer, db.ForeignKey('plagiarism_corpus.detection_id'), nullable=False, index=True)
    fragment_text = db.Column(db.Text, nullable=False)
    start_pos = db.Column(db.Integer, nullable=False)
    end_pos = db.Column(db.Integer, nullable=False)
    fragment_hash = db.Column(db.String(64), nullable=False, index=True)
    shingles_json = db.Column(db.Text, nullable=False)
    simhash = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

def init_database(app):
    """Инициализация базы данных с автоматической миграцией"""
    try:
        # Важно: регистрируем модели пользователей ДО create_all,
        # иначе ForeignKey('users.id') в Detection не сможет разрешиться.
        import core.user_database  # noqa: F401

        # Создаем директорию instance если её нет
        instance_dir = os.path.join(os.path.dirname(app.root_path), 'instance')
        if not os.path.exists(instance_dir):
            os.makedirs(instance_dir)
            print(f"[OK] Создана директория: {instance_dir}")
        
        # Создаем все таблицы
        with app.app_context():
            db.create_all()
            print("[OK] База данных инициализирована")
            
            # Проверяем нужна ли миграция (добавление новых полей)
            inspector = inspect(db.engine)
            if 'detection' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('detection')]
                
                # Обновленный список полей для миграции
                new_fields = [
                    'user_id',
                    'char_count',  # Новое поле для количества символов
                    'word_count', 'sentence_count', 'avg_sentence_length',
                    'punctuation_density', 'uppercase_ratio',
                    'russian_readability',
                    'type_token_ratio', 'hapax_ratio',
                    'burstiness', 'mtld_diversity', 'bigram_uniqueness', 'trigram_uniqueness',
                    'pronoun_bias_first_person', 'lexical_predictability',
                    'pangram_window_variance', 'pangram_ai_sentences_count', 'pangram_window_burstiness'
                ]
                
                missing_fields = [field for field in new_fields if field not in columns]
                
                if missing_fields:
                    print(f"[WARN] Обнаружены отсутствующие поля: {len(missing_fields)}")
                    print("[INFO] Выполняется автоматическая миграция...")
                    
                    # Простая миграция: добавляем недостающие столбцы с корректными типами
                    field_types = {
                        'user_id': 'INTEGER',
                        'char_count': 'INTEGER',
                        'word_count': 'INTEGER',
                        'sentence_count': 'INTEGER',
                        'paragraph_count': 'INTEGER',
                        'pangram_ai_sentences_count': 'INTEGER'
                    }

                    for field in missing_fields:
                        try:
                            field_type = field_types.get(field, 'REAL')
                            db.engine.execute(f'ALTER TABLE detection ADD COLUMN {field} {field_type}')
                            print(f"   [OK] Добавлено поле: {field} ({field_type})")
                        except Exception:
                            print(f"   [WARN] Поле уже существует или ошибка: {field}")
                    
                    print("[OK] Миграция завершена")
                else:
                    print("[OK] Все поля актуальны")

                # Миграция типа prediction: VARCHAR(100) -> TEXT (PostgreSQL)
                try:
                    db.session.execute(sql_text("ALTER TABLE detection ALTER COLUMN prediction TYPE TEXT"))
                    db.session.commit()
                    print("[OK] Тип поля detection.prediction обновлён до TEXT")
                except Exception as migration_error:
                    db.session.rollback()
                    print(f"[WARN] Не удалось обновить тип поля prediction (возможно уже TEXT): {migration_error}")
                    
    except Exception as e:
        print(f"[ERROR] Ошибка инициализации БД: {e}")
        # Если ошибка, создаем базовую структуру
        try:
            with app.app_context():
                db.create_all()
                print("[OK] Создана базовая структура БД")
        except Exception as e2:
            print(f"[ERROR] Критическая ошибка БД: {e2}")

def save_detection_with_features(filename, file_type, extracted_text, pangram_response, endpoint_type, text_features):
    """Сохранение результата детекции с расширенными признаками"""
    import statistics
    import numpy as np
    
    # Функция для конвертации numpy типов в Python типы
    def convert_numpy_types(value):
        if isinstance(value, (np.integer, np.floating)):
            return value.item()
        elif isinstance(value, np.ndarray):
            return value.tolist()
        return value
    
    # Нормализуем числовые поля Pangram (V3 + legacy)
    ai_likelihood = pangram_response.get('ai_likelihood')
    if ai_likelihood is None:
        ai_likelihood = pangram_response.get('fraction_ai')

    avg_ai_likelihood = pangram_response.get('avg_ai_likelihood')
    if avg_ai_likelihood is None:
        avg_ai_likelihood = ai_likelihood

    max_ai_likelihood = pangram_response.get('max_ai_likelihood')
    if max_ai_likelihood is None:
        max_ai_likelihood = ai_likelihood

    prediction = (
        pangram_response.get('prediction')
        or pangram_response.get('prediction_short')
        or pangram_response.get('headline')
    )

    fraction_ai_content = pangram_response.get('fraction_ai_content')
    if fraction_ai_content is None:
        fraction_ai_content = pangram_response.get('fraction_ai')

    # Создаем новую запись
    detection = Detection(
        filename=filename,
        file_type=file_type,
        text_length=len(extracted_text.split()),
        char_count=len(extracted_text),
        extracted_text=extracted_text,
        api_endpoint=endpoint_type,
        ai_likelihood=ai_likelihood,
        max_ai_likelihood=max_ai_likelihood,
        avg_ai_likelihood=avg_ai_likelihood,
        prediction=prediction,
        fraction_ai_content=fraction_ai_content,
        full_response=json.dumps(pangram_response, ensure_ascii=False),
        
        # Сохраняем только актуальные текстовые признаки (конвертируем numpy типы)
        word_count=convert_numpy_types(text_features.get('word_count')),
        sentence_count=convert_numpy_types(text_features.get('sentence_count')),
        avg_sentence_length=convert_numpy_types(text_features.get('avg_sentence_length')),
        punctuation_density=convert_numpy_types(text_features.get('punctuation_density')),
        uppercase_ratio=convert_numpy_types(text_features.get('uppercase_ratio')),
        
        # Признаки читаемости (обновлено для русского)
        russian_readability=convert_numpy_types(text_features.get('russian_readability')),
        
        # Лингвистические признаки (оптимизированные)
        type_token_ratio=convert_numpy_types(text_features.get('type_token_ratio')),
        hapax_ratio=convert_numpy_types(text_features.get('hapax_ratio')),
        
        # Новые эффективные признаки для детекции ИИ
        burstiness=convert_numpy_types(text_features.get('burstiness')),
        mtld_diversity=convert_numpy_types(text_features.get('mtld_diversity')),
        bigram_uniqueness=convert_numpy_types(text_features.get('bigram_uniqueness')),
        trigram_uniqueness=convert_numpy_types(text_features.get('trigram_uniqueness')),
        pronoun_bias_first_person=convert_numpy_types(text_features.get('pronoun_bias_first_person')),
        lexical_predictability=convert_numpy_types(text_features.get('lexical_predictability'))
    )
    
    # Дополнительные Pangram признаки
    if 'windows' in pangram_response and pangram_response['windows']:
        windows = pangram_response['windows']
        window_scores = []
        for window in windows:
            score = window.get('ai_likelihood')
            if score is None:
                score = window.get('ai_assistance_score')
            if score is not None:
                try:
                    window_scores.append(float(score))
                except (TypeError, ValueError):
                    pass
        if window_scores and len(window_scores) > 1:
            detection.pangram_window_variance = statistics.variance(window_scores)
            # Добавляем burstiness для окон
            mean_score = statistics.mean(window_scores)
            std_score = statistics.stdev(window_scores)
            detection.pangram_window_burstiness = std_score / mean_score if mean_score > 0 else 0
    
    if 'ai_sentences' in pangram_response:
        detection.pangram_ai_sentences_count = len(pangram_response['ai_sentences'])
    
    db.session.add(detection)
    db.session.commit()
    
    return detection 
