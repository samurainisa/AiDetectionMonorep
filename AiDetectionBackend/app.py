"""
Основное приложение Flask для системы детекции ИИ
"""
import os
import json
from datetime import datetime, timedelta
from io import BytesIO
import psycopg2
from sqlalchemy.engine import url as sa_url
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

load_dotenv()

# Импорт наших модулей
from core.database import db, init_database, Detection, save_detection_with_features
from core.feature_extractor import TextFeatureExtractor, extract_pangram_features
from core.pangram_client import analyze_text, call_pangram_api, determine_api_endpoint
from utils.file_processing import allowed_file, extract_text_from_file

# Импорт дополнительных систем
from plagiarism_engine import plagiarism_engine, PlagiarismLevel
from core.database import PlagiarismCheck
from training_service import initialize_training_service, get_training_service
from services.detection_service import analyze_and_store, get_optional_user_id

app = Flask(__name__)

PLAGIARISM_PENDING_WINDOW_SECONDS = int(os.getenv('PLAGIARISM_PENDING_WINDOW_SECONDS', 2 * 60 * 60))


def _plagiarism_status_for_detection(detection, has_report=False):
    if has_report:
        return 'ready'

    created_at = getattr(detection, 'created_at', None)
    if created_at:
        age = datetime.utcnow() - created_at
        if age <= timedelta(seconds=PLAGIARISM_PENDING_WINDOW_SECONDS):
            return 'pending'

    return 'unknown'


def _plagiarism_report_from_check(check):
    if not check:
        return None

    try:
        matches = json.loads(check.matches_json or '[]')
    except Exception:
        matches = []

    try:
        similar_documents = json.loads(check.similar_documents_json or '[]')
    except Exception:
        similar_documents = []

    return {
        'detection_id': check.detection_id,
        'total_similarity_score': check.similarity_percentage or 0,
        'plagiarism_level': check.plagiarism_level or 'original',
        'originality_percentage': check.originality_percentage,
        'total_fragments': check.total_fragments,
        'matched_fragments': check.matched_fragments,
        'matches': matches,
        'similar_documents': similar_documents,
    }

def _build_cors_origins():
    """
    Возвращает список/паттерны разрешённых origins.
    Локально разрешаем любые порты localhost/127.0.0.1, чтобы Vite не ломался при смене порта.
    """
    configured_origins = os.getenv("CORS_ORIGINS", "").strip()
    if configured_origins:
        return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]

    return [
        r"^https?://localhost(:\d+)?$",
        r"^https?://127\.0\.0\.1(:\d+)?$",
        "https://ai-detector-frontend-ten.vercel.app",
    ]


CORS(
    app,
    origins=_build_cors_origins(),
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization'],
    supports_credentials=True,
)

def get_env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"ENV переменная {name} не задана")
    return value

app.config['SECRET_KEY'] = get_env_required('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = get_env_required('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 32 * 1024 * 1024))

def ensure_database_exists(database_url: str) -> None:
    try:
        parsed = sa_url.make_url(database_url)
        dbname = parsed.database
        user = parsed.username or 'postgres'
        password = parsed.password or ''
        host = parsed.host or 'localhost'
        port = parsed.port or 5432
        conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host, port=port)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
        if cur.fetchone() is None:
            cur.execute(f'CREATE DATABASE "{dbname}"')
            print(f"[OK] Создана БД: {dbname}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[WARN] Не удалось проверить/создать БД: {e}")

# Инициализация БД
ensure_database_exists(app.config['SQLALCHEMY_DATABASE_URI'])
db.init_app(app)

# Инициализация экстрактора признаков
feature_extractor = TextFeatureExtractor()

@app.route('/', methods=['GET'])
def index():
    """Главная страница API"""
    return jsonify({
        'message': 'AI Detection Backend API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': [
            '/upload - POST - загрузка файла для анализа',
            '/analyze-text - POST - анализ текста напрямую',
            '/history - GET - история анализов',
            '/stats - GET - статистика',
            '/plagiarism/<id> - GET - отчет о плагиате'
        ]
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    """Загрузка и анализ файла"""
    try:
        user_id = get_optional_user_id(request)

        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400

        detailed_analysis = request.form.get('detailed_analysis', 'false').lower() == 'true'

        if not (file and allowed_file(file.filename)):
            return jsonify({'error': 'Неподдерживаемый тип файла'}), 400

        # Сохраняем файл и извлекаем текст
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            file_type = filename.rsplit('.', 1)[1].lower()
            extracted_text = extract_text_from_file(file_path, file_type)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

        # Минимальная длина текста — по количеству слов
        if len(extracted_text.split()) < 3:
            return jsonify({'error': 'Текст слишком короткий для анализа (минимум 3 слова)'}), 400

        response_data = analyze_and_store(
            extracted_text,
            filename=filename,
            file_type=file_type,
            detailed_analysis=detailed_analysis,
            user_id=user_id,
            feature_extractor=feature_extractor,
        )
        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze-text', methods=['POST'])
def analyze_text_endpoint():
    """Анализ текста напрямую"""
    try:
        user_id = get_optional_user_id(request)

        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Текст не предоставлен'}), 400

        text = data['text']
        detailed_analysis = data.get('detailed_analysis', False)

        # Минимальная длина текста — по количеству слов
        if len(text.split()) < 3:
            return jsonify({'error': 'Текст слишком короткий для анализа (минимум 3 слова)'}), 400

        response_data = analyze_and_store(
            text,
            filename='direct_text_input',
            file_type='text',
            detailed_analysis=detailed_analysis,
            user_id=user_id,
            feature_extractor=feature_extractor,
        )
        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_batch():
    """Батч анализ текстов"""
    try:
        data = request.get_json()
        if not data or 'texts' not in data:
            return jsonify({'error': 'Тексты не предоставлены'}), 400
        
        texts = data['texts']
        if not isinstance(texts, list) or len(texts) == 0:
            return jsonify({'error': 'Список текстов пуст'}), 400
        
        results = []
        for i, text in enumerate(texts):
            try:
                # Проверяем минимальную длину текста (по количеству слов, а не символов)
                word_count = len(text.split())
                if word_count < 3:  # ✅ Изменено: проверяем количество слов, а не символов
                    results.append({'error': 'Текст слишком короткий для анализа (минимум 3 слова)'})
                    continue
                
                # Анализируем через Pangram API
                pangram_response = call_pangram_api('batch', [text])
                if isinstance(pangram_response, list) and len(pangram_response) > 0:
                    pangram_response = pangram_response[0]
                
                # Извлекаем признаки
                text_features = feature_extractor.extract_features(text)
                
                # Сохраняем в БД
                detection = save_detection_with_features(
                    f'batch_text_{i+1}', 'text', text, pangram_response, 'batch', text_features
                )
                
                results.append({
                    'id': detection.id,
                    'ai_likelihood': detection.ai_likelihood,
                    'prediction': detection.prediction
                })
                
            except Exception as e:
                results.append({'error': str(e)})
        
        return jsonify({'results': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history', methods=['GET'])
def get_history():
    """Получение истории анализов с фильтрацией"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Отладка: выводим все параметры запроса
        print(f"[DEBUG] History request params: {dict(request.args)}")
        
        # Проверяем авторизацию для персонального пула
        user_id = None
        auth_header = request.headers.get('Authorization')
        print(f"[DEBUG] Auth header: {auth_header[:50] if auth_header else 'None'}...")
        
        if auth_header and auth_header.startswith('Bearer '):
            try:
                from auth import AuthService
                token = auth_header[7:]  # Убираем 'Bearer '
                print(f"[DEBUG] Token: {token[:20]}...")
                payload = AuthService.verify_token(token)
                user_id = payload.get('user_id')
                print(f"[DEBUG] Authenticated user: {user_id}")
            except Exception as e:
                print(f"[DEBUG] Auth error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': 'Недействительный токен авторизации'}), 401
        else:
            print(f"[DEBUG] No valid auth header found")
            return jsonify({'error': 'Требуется авторизация'}), 401
        
        # Параметры фильтрации (поддерживаем разные варианты названий)
        prediction_filter = request.args.get('prediction') or request.args.get('predictionFilter')
        file_type_filter = request.args.get('file_type') or request.args.get('fileType') or request.args.get('fileTypeFilter')
        date_from = request.args.get('dateFrom') or request.args.get('date_from')
        date_to = request.args.get('dateTo') or request.args.get('date_to')
        search_query = request.args.get('search') or request.args.get('searchQuery') or request.args.get('q')
        ai_likelihood_min = request.args.get('ai_likelihood_min', type=float) or request.args.get('aiLikelihoodMin', type=float)
        ai_likelihood_max = request.args.get('ai_likelihood_max', type=float) or request.args.get('aiLikelihoodMax', type=float)
        
        print(f"[DEBUG] Parsed filters: prediction={prediction_filter}, file_type={file_type_filter}, search={search_query}")
        
        # Базовый запрос с фильтрацией по пользователю
        query = Detection.query
        # Личный пул: владелец в Detection.user_id или в legacy-связи user_detections
        from core.user_database import DetectionModel
        query = query.outerjoin(DetectionModel, Detection.id == DetectionModel.original_detection_id)
        query = query.filter(
            db.or_(
                Detection.user_id == user_id,
                DetectionModel.user_id == user_id
            )
        )
        
        # Фильтр по типу предсказания
        if prediction_filter:
            if prediction_filter == 'AI':
                query = query.filter(Detection.ai_likelihood > 0.5)
            elif prediction_filter == 'HUMAN':
                query = query.filter(Detection.ai_likelihood <= 0.5)
        
        # Фильтр по типу файла
        if file_type_filter:
            query = query.filter(Detection.file_type == file_type_filter)
        
        # Фильтр по дате
        if date_from:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Detection.created_at >= date_from_obj)
        
        if date_to:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Добавляем время до конца дня
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            query = query.filter(Detection.created_at <= date_to_obj)
        
        # Фильтр по поиску (filename или extracted_text)
        if search_query:
            search_pattern = f'%{search_query}%'
            query = query.filter(
                db.or_(
                    Detection.filename.ilike(search_pattern),
                    Detection.extracted_text.ilike(search_pattern)
                )
            )
        
        # Фильтр по диапазону AI likelihood
        if ai_likelihood_min is not None and ai_likelihood_min >= 0:
            query = query.filter(Detection.ai_likelihood >= ai_likelihood_min)
            print(f"[DEBUG] Added ai_likelihood_min filter: {ai_likelihood_min}")
        
        if ai_likelihood_max is not None and ai_likelihood_max <= 1:
            query = query.filter(Detection.ai_likelihood <= ai_likelihood_max)
            print(f"[DEBUG] Added ai_likelihood_max filter: {ai_likelihood_max}")
            
        print(f"[DEBUG] Final query ready for user {user_id}")
        
        # Пагинация
        detections = query.order_by(Detection.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        detection_list = []
        for d in detections.items:
            detection_data = {
                'id': d.id,
                'filename': d.filename,
                'file_type': d.file_type,
                'api_endpoint': d.api_endpoint,
                'ai_likelihood': d.ai_likelihood,
                'prediction': d.prediction,
                'created_at': d.created_at.isoformat(),
                'text_length': d.text_length
            }
            
            # Добавляем краткую информацию о плагиате (из БД, fallback на in-memory)
            try:
                from core.database import PlagiarismCheck
                pc = PlagiarismCheck.query.filter_by(detection_id=d.id).order_by(PlagiarismCheck.created_at.desc()).first()
                if pc:
                    detection_data['plagiarism_originality'] = pc.originality_percentage
                    detection_data['plagiarism_similarity'] = pc.similarity_percentage
                    detection_data['plagiarism_level'] = pc.plagiarism_level
                    detection_data['plagiarism_status'] = 'ready'
                else:
                    report = plagiarism_engine.get_report(d.id)
                    if report:
                        detection_data['plagiarism_originality'] = report.originality_percentage
                        detection_data['plagiarism_similarity'] = 100 - report.originality_percentage
                        detection_data['plagiarism_level'] = report.plagiarism_level.value
                        detection_data['plagiarism_status'] = 'ready'
            except Exception:
                pass  # Игнорируем ошибки получения данных о плагиате
            
            if 'plagiarism_status' not in detection_data:
                detection_data['plagiarism_status'] = _plagiarism_status_for_detection(d)
            detection_data['plagiarism_pending'] = detection_data['plagiarism_status'] == 'pending'
            
            detection_list.append(detection_data)
        
        return jsonify({
            'detections': detection_list,
            'total': detections.total,
            'pages': detections.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history/<int:detection_id>', methods=['GET'])
def get_detection(detection_id):
    """Получение детальной информации о детекции"""
    try:
        detection = Detection.query.get_or_404(detection_id)
        
        # Структурируем признаки для фронтенда (только актуальные поля)
        # Используем getattr с значениями по умолчанию для безопасности
        text_features = {
            'basic': {
                'word_count': getattr(detection, 'word_count', None),
                'sentence_count': getattr(detection, 'sentence_count', None),
                'avg_sentence_length': getattr(detection, 'avg_sentence_length', None),
                'punctuation_density': getattr(detection, 'punctuation_density', None),
                'uppercase_ratio': getattr(detection, 'uppercase_ratio', None)
            },
            'readability': {
                'russian_readability': getattr(detection, 'russian_readability', None)
            },
            'linguistic': {
                'type_token_ratio': getattr(detection, 'type_token_ratio', None),
                'hapax_ratio': getattr(detection, 'hapax_ratio', None)
            },
            'ai_detection': {
                'burstiness': getattr(detection, 'burstiness', None),
                'mtld_diversity': getattr(detection, 'mtld_diversity', None),
                'bigram_uniqueness': getattr(detection, 'bigram_uniqueness', None),
                'trigram_uniqueness': getattr(detection, 'trigram_uniqueness', None),
                'pronoun_bias_first_person': getattr(detection, 'pronoun_bias_first_person', None),
                'lexical_predictability': getattr(detection, 'lexical_predictability', None)
            },
            'pangram_extended': {
                'pangram_window_variance': getattr(detection, 'pangram_window_variance', None),
                'pangram_ai_sentences_count': getattr(detection, 'pangram_ai_sentences_count', None),
                'pangram_window_burstiness': getattr(detection, 'pangram_window_burstiness', None)
            }
        }
        
        # Парсим full_response из JSON
        full_response = {}
        if detection.full_response:
            try:
                full_response = json.loads(detection.full_response)
            except json.JSONDecodeError:
                full_response = {}
        
        # Получаем отчет о плагиате если есть
        plagiarism_report = None
        try:
            pc = PlagiarismCheck.query.filter_by(detection_id=detection.id).order_by(PlagiarismCheck.created_at.desc()).first()
            if pc:
                plagiarism_report = _plagiarism_report_from_check(pc)
            else:
                report = plagiarism_engine.get_report(detection.id)
                if report:
                    plagiarism_report = report.to_dict()
        except Exception as e:
            print(f"[WARN] Ошибка получения отчета о плагиате: {e}")
        
        plagiarism_status = _plagiarism_status_for_detection(detection, has_report=bool(plagiarism_report))

        response_data = {
            'id': detection.id,
            'filename': detection.filename,
            'file_type': detection.file_type,
            'text_length': detection.text_length,
            'extracted_text': detection.extracted_text,
            'ai_likelihood': detection.ai_likelihood,
            'max_ai_likelihood': detection.max_ai_likelihood,
            'avg_ai_likelihood': detection.avg_ai_likelihood,
            'prediction': detection.prediction,
            'fraction_ai_content': detection.fraction_ai_content,
            'api_endpoint': detection.api_endpoint,
            'created_at': detection.created_at.isoformat(),
            'full_response': full_response,
            'text_features': text_features,
            'plagiarism_status': plagiarism_status,
            'plagiarism_pending': plagiarism_status == 'pending',
        }
        
        # Добавляем данные о плагиате если есть
        if plagiarism_report:
            response_data['plagiarism_report'] = plagiarism_report
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Получение общей статистики"""
    try:
        total_count = Detection.query.count()
        ai_count = Detection.query.filter(Detection.ai_likelihood > 0.5).count()
        human_count = total_count - ai_count
        
        # Средняя вероятность ИИ
        avg_ai_likelihood = db.session.query(db.func.avg(Detection.ai_likelihood)).filter(
            Detection.ai_likelihood.isnot(None)
        ).scalar() or 0
        
        # Анализы за последние 7 дней
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_count = Detection.query.filter(Detection.created_at >= week_ago).count()
        
        return jsonify({
            'total_analyses': total_count,
            'ai_generated': ai_count,
            'human_generated': human_count,
            'avg_ai_likelihood': round(avg_ai_likelihood, 3) if avg_ai_likelihood else 0,
            'recent_analyses': recent_count,
            'ai_percentage': round((ai_count / total_count * 100), 1) if total_count > 0 else 0
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/filter-options', methods=['GET'])
def get_filter_options():
    """Получение опций для фильтрации"""
    try:
        # Уникальные типы файлов
        file_types = db.session.query(Detection.file_type).distinct().all()
        file_types = [ft[0] for ft in file_types if ft[0]]
        
        # Уникальные типы API endpoints
        api_endpoints = db.session.query(Detection.api_endpoint).distinct().all()
        api_endpoints = [ep[0] for ep in api_endpoints if ep[0]]
        
        return jsonify({
            'file_types': file_types,
            'api_endpoints': api_endpoints,
            'prediction_types': [
                {'value': 'AI', 'label': 'ИИ-контент'},
                {'value': 'HUMAN', 'label': 'Человеческий контент'}
            ],
            'ai_likelihood_ranges': [
                {'label': 'Очень высокая (80-100%)', 'min': 0.8, 'max': 1.0},
                {'label': 'Высокая (60-80%)', 'min': 0.6, 'max': 0.8},
                {'label': 'Средняя (40-60%)', 'min': 0.4, 'max': 0.6},
                {'label': 'Низкая (20-40%)', 'min': 0.2, 'max': 0.4},
                {'label': 'Очень низкая (0-20%)', 'min': 0.0, 'max': 0.2}
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Импортируем дополнительные routes
from routes.detector_routes import register_detector_routes
from routes.auth_routes import register_auth_routes
from routes.report_routes import register_report_routes

register_detector_routes(app, get_training_service)
register_auth_routes(app)
register_report_routes(app)

# API endpoints для антиплагиата
@app.route('/plagiarism/<int:detection_id>', methods=['GET'])
def get_plagiarism_report(detection_id):
    """Get plagiarism report for a detection."""
    try:
        detection = Detection.query.get_or_404(detection_id)

        # Source of truth is plagiarism_checks table. In-memory engine is a fallback.
        try:
            pc = PlagiarismCheck.query.filter_by(detection_id=detection_id).order_by(PlagiarismCheck.created_at.desc()).first()
        except Exception:
            pc = None

        report_dict = None
        if pc:
            try:
                matches_list = json.loads(pc.matches_json or '[]')
            except Exception:
                matches_list = []
            try:
                similar_docs_list = json.loads(pc.similar_documents_json or '[]')
            except Exception:
                similar_docs_list = []

            report_dict = {
                'detection_id': detection_id,
                'total_similarity_score': None,
                'plagiarism_level': pc.plagiarism_level or 'original',
                'originality_percentage': pc.originality_percentage if pc.originality_percentage is not None else 100.0,
                'total_fragments': pc.total_fragments if pc.total_fragments is not None else 0,
                'matched_fragments': pc.matched_fragments if pc.matched_fragments is not None else len(matches_list),
                'matches': matches_list,
                'similar_documents': similar_docs_list,
            }
        else:
            status = _plagiarism_status_for_detection(detection)
            if status == 'pending':
                return jsonify({
                    'detection_id': detection.id,
                    'plagiarism_status': 'pending',
                    'plagiarism_pending': True,
                    'message': 'Антиплагиат рассчитывается',
                }), 202

            try:
                prev_docs = Detection.query.filter(
                    Detection.filename == detection.filename,
                    Detection.id != detection.id,
                ).order_by(Detection.created_at.desc()).limit(50).all()

                for prev in prev_docs:
                    plagiarism_engine.add_document_to_corpus(prev.id, prev.filename, prev.extracted_text)

                plagiarism_engine.add_document_to_corpus(detection.id, detection.filename, detection.extracted_text)
                report = plagiarism_engine.check_plagiarism(detection.id, detection.extracted_text, detection.filename)
                report_dict = report.to_dict()

                try:
                    pc_new = PlagiarismCheck(
                        detection_id=detection.id,
                        user_id=None,
                        filename=detection.filename,
                        similarity_percentage=100 - report_dict.get('originality_percentage', 100.0),
                        originality_percentage=report_dict.get('originality_percentage', 100.0),
                        plagiarism_level=report_dict.get('plagiarism_level', 'original'),
                        total_fragments=report_dict.get('total_fragments', 0),
                        matched_fragments=report_dict.get('matched_fragments', 0),
                        matches_json=json.dumps(report_dict.get('matches', []), ensure_ascii=False),
                        similar_documents_json=json.dumps(report_dict.get('similar_documents', []), ensure_ascii=False),
                    )
                    db.session.add(pc_new)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
            except Exception:
                return jsonify({'error': 'Plagiarism report not found'}), 404

        if not report_dict:
            return jsonify({'error': 'Plagiarism report not found'}), 404

        matches = report_dict.get('matches', []) or []

        # Recalculate originality from matches if clearly inconsistent.
        try:
            original_value = float(report_dict.get('originality_percentage', 100) or 100)
            if matches and original_value >= 99.9:
                by_pos = {}
                for match in matches:
                    position = match.get('target_fragment_pos')
                    similarity = float(match.get('similarity_score', 0) or 0)
                    if similarity > 1:
                        similarity = similarity / 100.0
                    by_pos.setdefault(position, []).append(similarity)
                totals = [max(values) for values in by_pos.values() if values]
                average_similarity = (sum(totals) / len(totals)) if totals else 0.0
                report_dict['originality_percentage'] = max(0.0, 100.0 - average_similarity * 100.0)
        except Exception:
            pass

        try:
            originality = float(report_dict.get('originality_percentage', 100) or 100)
        except Exception:
            originality = 100.0
        originality = max(0.0, min(100.0, originality))

        if originality >= 85:
            plagiarism_level = 'original'
        elif originality >= 70:
            plagiarism_level = 'low'
        elif originality >= 50:
            plagiarism_level = 'moderate'
        elif originality >= 30:
            plagiarism_level = 'high'
        else:
            plagiarism_level = 'very_high'

        normalized_matches = []
        source_stats = {}
        for match in matches:
            try:
                similarity_raw = float(match.get('similarity_score', 0) or 0)
            except Exception:
                similarity_raw = 0.0

            similarity_score = similarity_raw / 100.0 if similarity_raw > 1 else similarity_raw
            similarity_score = max(0.0, min(1.0, similarity_score))

            source_detection_id_raw = match.get('source_detection_id')
            try:
                source_detection_id = int(source_detection_id_raw) if source_detection_id_raw is not None else None
            except Exception:
                source_detection_id = None
            source_filename = match.get('source_filename')
            if not source_filename and source_detection_id:
                source_doc = Detection.query.get(source_detection_id)
                if source_doc:
                    source_filename = source_doc.filename

            matched_text = str(
                match.get('matched_text')
                or match.get('source_text')
                or match.get('target_text')
                or ''
            ).strip()
            if not matched_text:
                continue

            normalized_match = {
                'source_detection_id': source_detection_id,
                'source_fragment_pos': int(match.get('source_fragment_pos') or 0),
                'target_fragment_pos': int(match.get('target_fragment_pos') or 0),
                'similarity_score': similarity_score,
                'matched_text': matched_text,
                'match_type': match.get('match_type', 'text_similarity'),
                'source_filename': source_filename or 'Unknown source',
            }
            normalized_matches.append(normalized_match)

            if source_detection_id:
                stats = source_stats.setdefault(source_detection_id, {
                    'matched_fragments': 0,
                    'max_similarity': 0.0,
                    'filename': normalized_match['source_filename'],
                })
                stats['matched_fragments'] += 1
                stats['max_similarity'] = max(stats['max_similarity'], similarity_score)

        raw_similar_documents = report_dict.get('similar_documents', []) or []
        normalized_similar_documents = []
        if isinstance(raw_similar_documents, list) and raw_similar_documents:
            for index, doc in enumerate(raw_similar_documents):
                source_detection_id = doc.get('detection_id') or doc.get('source_detection_id') or (index + 1)
                try:
                    source_detection_id = int(source_detection_id)
                except Exception:
                    source_detection_id = index + 1

                stats = source_stats.get(source_detection_id, {})
                similarity_percentage = doc.get('similarity_percentage')
                if similarity_percentage is None:
                    similarity_percentage = stats.get('max_similarity', 0.0) * 100.0

                matched_fragments = doc.get('matched_fragments')
                if matched_fragments is None:
                    matched_fragments = stats.get('matched_fragments', 0)

                normalized_similar_documents.append({
                    'detection_id': source_detection_id,
                    'filename': doc.get('filename') or doc.get('source_filename') or stats.get('filename') or f'Source #{source_detection_id}',
                    'similarity_percentage': float(similarity_percentage or 0),
                    'matched_fragments': int(matched_fragments or 0),
                    'created_at': doc.get('created_at') or '',
                })
        else:
            for source_detection_id, stats in source_stats.items():
                normalized_similar_documents.append({
                    'detection_id': source_detection_id,
                    'filename': stats.get('filename') or f'Source #{source_detection_id}',
                    'similarity_percentage': float(stats.get('max_similarity', 0.0) * 100.0),
                    'matched_fragments': int(stats.get('matched_fragments', 0)),
                    'created_at': '',
                })

        response_payload = {
            'detection_id': detection_id,
            'filename': detection.filename,
            'word_count': detection.text_length,
            'created_at': detection.created_at.isoformat(),
            'originality_percentage': originality,
            'plagiarism_level': plagiarism_level,
            'total_similarity_score': report_dict.get('total_similarity_score'),
            'total_fragments': int(report_dict.get('total_fragments') or len(normalized_matches)),
            'matched_fragments': int(report_dict.get('matched_fragments') or len(normalized_matches)),
            'matches_count': len(normalized_matches),
            'sources_count': len(normalized_similar_documents),
            'matches': normalized_matches,
            'similar_documents': normalized_similar_documents,
        }

        return jsonify(response_payload)

    except Exception as e:
        print(f"[ERROR] Plagiarism report error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _safe_pdf_text(value):
    """ReportLab's built-in fonts are latin-1 only; replace unsupported chars."""
    if value is None:
        return ''
    return str(value).encode('latin-1', errors='replace').decode('latin-1')


@app.route('/plagiarism/<int:detection_id>/pdf', methods=['GET'])
def download_plagiarism_report_pdf(detection_id):
    """Generate a compact PDF report for plagiarism details."""
    try:
        report_response = get_plagiarism_report(detection_id)
        status_code = 200
        response_obj = report_response

        if isinstance(report_response, tuple):
            response_obj, status_code = report_response

        if status_code != 200:
            return report_response

        payload = response_obj.get_json(silent=True) if hasattr(response_obj, 'get_json') else None
        if not payload:
            return jsonify({'error': 'Plagiarism report not found'}), 404

        pdf_buffer = BytesIO()
        pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=A4)
        page_width, page_height = A4
        y_position = page_height - 48

        def draw_line(text, font_name='Helvetica', font_size=10, step=14):
            nonlocal y_position
            if y_position < 48:
                pdf_canvas.showPage()
                y_position = page_height - 48
            pdf_canvas.setFont(font_name, font_size)
            pdf_canvas.drawString(48, y_position, _safe_pdf_text(text))
            y_position -= step

        plagiarism_value = round(100 - float(payload.get('originality_percentage', 100)))
        draw_line(f'Plagiarism Report #{detection_id}', font_name='Helvetica-Bold', font_size=14, step=20)
        draw_line(f"Filename: {payload.get('filename', f'Document #{detection_id}')}")
        draw_line(f"Created at: {payload.get('created_at', '-')}")
        draw_line(f"Originality: {round(float(payload.get('originality_percentage', 100)), 2)}%")
        draw_line(f'Plagiarism: {plagiarism_value}%')
        draw_line(f"Level: {payload.get('plagiarism_level', 'original')}")
        draw_line(f"Sources: {payload.get('sources_count', 0)}")
        draw_line(f"Matches: {payload.get('matches_count', 0)}", step=20)

        similar_documents = payload.get('similar_documents') or []
        draw_line('Top similar documents:', font_name='Helvetica-Bold')
        if not similar_documents:
            draw_line('- No sources found')
        else:
            for source in similar_documents[:20]:
                source_name = source.get('filename', f"Source #{source.get('detection_id', '?')}")
                source_similarity = round(float(source.get('similarity_percentage', 0)), 2)
                source_fragments = int(source.get('matched_fragments', 0))
                draw_line(f"- {source_name} | {source_similarity}% | fragments: {source_fragments}")

        matches = payload.get('matches') or []
        draw_line('', step=8)
        draw_line('Top matched fragments:', font_name='Helvetica-Bold')
        if not matches:
            draw_line('- No matched fragments')
        else:
            for index, match in enumerate(matches[:20], start=1):
                similarity_value = match.get('similarity_score', 0)
                try:
                    similarity_value = float(similarity_value)
                except Exception:
                    similarity_value = 0.0
                similarity_percent = round(similarity_value * 100 if similarity_value <= 1 else similarity_value, 2)
                fragment_preview = str(match.get('matched_text', '')).replace('\n', ' ').strip()
                if len(fragment_preview) > 95:
                    fragment_preview = f'{fragment_preview[:95]}...'
                draw_line(f'{index}. {similarity_percent}% | {fragment_preview}')

        pdf_canvas.save()
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'plagiarism-{detection_id}.pdf',
        )

    except Exception as e:
        print(f"[ERROR] Failed to generate plagiarism PDF: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/plagiarism/corpus-stats', methods=['GET'])
def get_corpus_stats():
    """Получение статистики корпуса документов"""
    try:
        stats = plagiarism_engine.get_corpus_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/plagiarism/recheck/<int:detection_id>', methods=['POST'])
def recheck_plagiarism(detection_id):
    """Повторная проверка документа на плагиат"""
    try:
        # Получаем текст из базы данных
        detection = Detection.query.get_or_404(detection_id)
        
        # Проверяем плагиат заново
        report = plagiarism_engine.check_plagiarism(
            detection_id, 
            detection.extracted_text, 
            detection.filename
        )
        
        return jsonify(report.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extract-text', methods=['POST'])
def extract_text_only():
    """Извлечение текста из файла без анализа"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Неподдерживаемый тип файла'}), 400
        
        # Сохраняем файл временно
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Извлекаем текст
            file_type = filename.rsplit('.', 1)[1].lower()
            extracted_text = extract_text_from_file(file_path, file_type)
            
            # Подсчитываем слова
            word_count = len(extracted_text.split())
            
            return jsonify({
                'extracted_text': extracted_text,
                'word_count': word_count,
                'char_count': len(extracted_text),
                'filename': filename,
                'file_type': file_type
            })
            
        finally:
            # Удаляем временный файл
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/file-info', methods=['POST'])
def get_file_info():
    """Получение информации о файле (количество слов, символов) без извлечения полного текста"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Неподдерживаемый тип файла'}), 400
        
        # Сохраняем файл временно
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Извлекаем текст
            file_type = filename.rsplit('.', 1)[1].lower()
            extracted_text = extract_text_from_file(file_path, file_type)
            
            # Подсчитываем только метрики, не возвращаем сам текст
            word_count = len(extracted_text.split())
            char_count = len(extracted_text)
            
            return jsonify({
                'word_count': word_count,
                'char_count': char_count,
                'filename': filename,
                'file_type': file_type
            })
            
        finally:
            # Удаляем временный файл
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'Файл слишком большой'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Ресурс не найден'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

if __name__ == '__main__':
    # Создаем папку для загрузок
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Инициализируем БД и пользовательские таблицы
    init_database(app)
    with app.app_context():
        from core.user_database import init_user_database
        init_user_database()
    
    print("[OK] Сервер запущен на http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000) 
