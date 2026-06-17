"""
Сервисный слой анализа текста.

Содержит общий пайплайн, который раньше дублировался между
эндпоинтами /upload и /analyze-text: вызов Pangram, извлечение признаков,
сохранение детекции, привязка владельца, пересчёт плагиата и сборка ответа.
"""
import json

from core.database import (
    db,
    Detection,
    PlagiarismCheck,
    save_detection_with_features,
)
from core.pangram_client import analyze_text, determine_api_endpoint
from plagiarism_engine import plagiarism_engine


def get_optional_user_id(request) -> int | None:
    """Достаёт user_id из Bearer-токена, если он валиден.

    Ошибки авторизации намеренно игнорируются: эндпоинты анализа доступны
    и анонимно, токен лишь привязывает результат к пользователю.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    try:
        from auth import AuthService
        payload = AuthService.verify_token(auth_header[7:])
        return payload.get('user_id')
    except Exception:
        return None


def analyze_and_store(text, *, filename, file_type, detailed_analysis, user_id, feature_extractor):
    """Полный цикл анализа одного текста и сохранения результата.

    Возвращает словарь ответа (detection + pangram_response + plagiarism_report).
    """
    pangram_response = analyze_text(text, detailed_analysis=detailed_analysis)
    text_features = feature_extractor.extract_features(text)

    detection = save_detection_with_features(
        filename,
        file_type,
        text,
        pangram_response,
        determine_api_endpoint(len(text.split()), detailed_analysis=detailed_analysis),
        text_features,
    )

    _attach_owner(detection, user_id)
    _link_user_detection(detection, user_id)
    plagiarism_report = _recompute_plagiarism(detection, text, filename)

    response_data = {
        'detection_id': detection.id,
        'filename': detection.filename,
        'file_type': detection.file_type,
        'text_length': detection.text_length,
        'api_endpoint_used': detection.api_endpoint,
        'pangram_response': {
            'headline': pangram_response.get('headline'),
            'ai_likelihood': detection.ai_likelihood,
            'max_ai_likelihood': detection.max_ai_likelihood,
            'avg_ai_likelihood': detection.avg_ai_likelihood,
            'prediction': detection.prediction,
            'prediction_short': pangram_response.get('prediction_short'),
            'fraction_ai_content': detection.fraction_ai_content,
            'fraction_ai': pangram_response.get('fraction_ai'),
            'fraction_ai_assisted': pangram_response.get('fraction_ai_assisted'),
            'fraction_human': pangram_response.get('fraction_human'),
            'llm_prediction': pangram_response.get('llm_prediction') or {},
            'windows': pangram_response.get('windows') or [],
        },
    }

    if plagiarism_report:
        report_dict = plagiarism_report.to_dict()
        response_data['plagiarism_report'] = report_dict
        _persist_plagiarism_check(detection, user_id, report_dict)

    return response_data


def _attach_owner(detection, user_id):
    """Привязывает владельца к самой детекции (поле user_id)."""
    if not user_id or not hasattr(detection, 'user_id') or detection.user_id is not None:
        return
    try:
        detection.user_id = user_id
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[WARN] Не удалось привязать владельца к детекции: {e}")


def _link_user_detection(detection, user_id):
    """Создаёт legacy-связь в user_detections для обратной совместимости."""
    if not user_id:
        return
    try:
        from core.user_database import DetectionModel
        user_detection = DetectionModel(
            user_id=user_id,
            original_detection_id=detection.id,
            is_public=False,
        )
        db.session.add(user_detection)
        db.session.commit()
        print(f"[DEBUG] Created user detection link for user {user_id}")
    except Exception as e:
        db.session.rollback()
        print(f"[WARN] Failed to create user detection link: {e}")


def _recompute_plagiarism(detection, text, filename):
    """Индексирует прошлые версии файла и пересчитывает плагиат для текущей детекции."""
    try:
        try:
            prev_docs = Detection.query.filter(
                Detection.filename == filename,
                Detection.id != detection.id,
            ).order_by(Detection.created_at.desc()).limit(50).all()
            for pd in prev_docs:
                plagiarism_engine.add_document_to_corpus(pd.id, pd.filename, pd.extracted_text)
        except Exception:
            pass
        plagiarism_engine.add_document_to_corpus(detection.id, filename, text)
        return plagiarism_engine.check_plagiarism(detection.id, text, filename)
    except Exception as e:
        print(f"[WARN] Ошибка проверки плагиата: {e}")
        return None


def _persist_plagiarism_check(detection, user_id, report_dict):
    """Сохраняет отчёт о плагиате в таблицу plagiarism_checks."""
    try:
        check = PlagiarismCheck(
            detection_id=detection.id,
            user_id=user_id,
            filename=detection.filename,
            similarity_percentage=100 - report_dict.get('originality_percentage', 100.0),
            originality_percentage=report_dict.get('originality_percentage', 100.0),
            plagiarism_level=report_dict.get('plagiarism_level', 'original'),
            total_fragments=report_dict.get('total_fragments', 0),
            matched_fragments=report_dict.get('matched_fragments', 0),
            matches_json=json.dumps(report_dict.get('matches', []), ensure_ascii=False),
            similar_documents_json=json.dumps(report_dict.get('similar_documents', []), ensure_ascii=False),
        )
        db.session.add(check)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[WARN] Не удалось сохранить PlagiarismCheck: {e}")
