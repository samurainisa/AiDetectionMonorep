"""
Маршруты для работы с детектором и экспортом данных
"""
import os
import json
import pandas as pd
from flask import request, jsonify, send_from_directory
from core.database import Detection, db
from core.feature_extractor import extract_pangram_features

def register_detector_routes(app, get_training_service):
    """Регистрирует маршруты детектора"""
    
    @app.route('/detector/status', methods=['GET'])
    def get_detector_status():
        """Статус детектора"""
        try:
            training_service = get_training_service()
            if training_service:
                status = training_service.get_training_status()
                return jsonify(status)
            else:
                return jsonify({'status': 'unavailable', 'message': 'Сервис обучения недоступен'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/detector/dataset/export', methods=['POST'])
    def export_dataset():
        """Экспорт датасета для обучения"""
        try:
            data = request.get_json() or {}
            format_type = data.get('format', 'csv')  # csv или json
            include_text = data.get('include_text', False)
            limit = data.get('limit', None)
            
            # Получаем данные из базы
            query = Detection.query.order_by(Detection.created_at.desc())
            if limit:
                query = query.limit(limit)
            
            detections = query.all()
            
            if not detections:
                return jsonify({'error': 'Нет данных для экспорта'}), 400
            
            processed_data = []
            
            for detection in detections:
                try:
                    row = {
                        'extracted_text': detection.extracted_text if include_text else '',
                        'text_length': detection.text_length,
                        'ai_likelihood': detection.ai_likelihood,
                        'max_ai_likelihood': detection.max_ai_likelihood,
                        'avg_ai_likelihood': detection.avg_ai_likelihood,
                        'fraction_ai_content': detection.fraction_ai_content,
                        
                        # Базовые статистические признаки
                        'word_count': getattr(detection, 'word_count', None),
                        'sentence_count': getattr(detection, 'sentence_count', None),
                        'avg_sentence_length': getattr(detection, 'avg_sentence_length', None),
                        'punctuation_density': getattr(detection, 'punctuation_density', None),
                        'uppercase_ratio': getattr(detection, 'uppercase_ratio', None),
                        
                        # Признаки читаемости (обновлено)
                        'russian_readability': getattr(detection, 'russian_readability', None),
                        
                        # Лингвистические признаки (оптимизированные)
                        'type_token_ratio': getattr(detection, 'type_token_ratio', None),
                        'hapax_ratio': getattr(detection, 'hapax_ratio', None),
                        
                        # Новые эффективные признаки для детекции ИИ
                        'burstiness': getattr(detection, 'burstiness', None),
                        'mtld_diversity': getattr(detection, 'mtld_diversity', None),
                        'bigram_uniqueness': getattr(detection, 'bigram_uniqueness', None),
                        'trigram_uniqueness': getattr(detection, 'trigram_uniqueness', None),
                        'pronoun_bias_first_person': getattr(detection, 'pronoun_bias_first_person', None),
                        'lexical_predictability': getattr(detection, 'lexical_predictability', None),
                        
                        # Дополнительные Pangram признаки
                        'pangram_window_variance': getattr(detection, 'pangram_window_variance', None),
                        # pangram_ai_sentences_count исключен - API не возвращает данные
                        'pangram_window_burstiness': getattr(detection, 'pangram_window_burstiness', None)
                    }
                    
                    # Добавляем признаки из Pangram full_response
                    if detection.full_response:
                        try:
                            full_response = json.loads(detection.full_response)
                            pangram_features = extract_pangram_features(full_response)
                            row.update(pangram_features)
                        except:
                            # Если ошибка парсинга, добавляем нулевые значения
                            row.update({
                                'high_ai_sentences_count': 0,
                                'avg_ai_sentence_prob': 0,
                                'window_count': 0,
                                'max_window_prob': 0,
                                'min_window_prob': 0,
                                'window_prob_std': 0
                            })
                    
                    # Добавляем дополнительные признаки для ML (убрали char_count - дублирует text_length)
                    row['is_ai_generated'] = 1 if detection.ai_likelihood and detection.ai_likelihood > 0.5 else 0
                    
                    # Категоризация риска
                    if detection.ai_likelihood:
                        if detection.ai_likelihood > 0.8:
                            row['ai_risk_category'] = 'high'
                        elif detection.ai_likelihood > 0.5:
                            row['ai_risk_category'] = 'medium'
                        else:
                            row['ai_risk_category'] = 'low'
                    else:
                        row['ai_risk_category'] = 'unknown'
                    
                    processed_data.append(row)
                    
                except Exception as e:
                    print(f"Ошибка обработки записи {detection.id}: {e}")
                    continue
            
            if not processed_data:
                return jsonify({'error': 'Не удалось обработать данные'}), 500
            
            # Создаем DataFrame
            df = pd.DataFrame(processed_data)
            
            # Заполняем NaN значения
            df = df.fillna(0)
            
            # Сохраняем файл
            os.makedirs('exports', exist_ok=True)
            filename = f'ai_detection_dataset_{len(processed_data)}_samples.{format_type}'
            filepath = os.path.join('exports', filename)
            
            if format_type == 'csv':
                df.to_csv(filepath, index=False, encoding='utf-8')
            elif format_type == 'json':
                df.to_json(filepath, orient='records', force_ascii=False, indent=2)
            
            return jsonify({
                'message': f'Датасет экспортирован: {filename}',
                'filename': filename,
                'samples_count': len(processed_data),
                'features_count': len(df.columns),
                'download_url': f'/detector/dataset/download/{filename}'
            })
            
        except Exception as e:
            return jsonify({'error': f'Ошибка экспорта: {str(e)}'}), 500

    @app.route('/detector/dataset/download/<filename>', methods=['GET'])
    def download_dataset(filename):
        """Скачивание экспортированного датасета"""
        try:
            return send_from_directory('exports', filename, as_attachment=True)
        except FileNotFoundError:
            return jsonify({'error': 'Файл не найден'}), 404

    @app.route('/detector/dataset/stats', methods=['GET'])
    def get_dataset_stats():
        """Статистика датасета"""
        try:
            total_count = Detection.query.count()
            ai_count = Detection.query.filter(Detection.ai_likelihood > 0.5).count()
            human_count = total_count - ai_count
            
            return jsonify({
                'total_samples': total_count,
                'ai_samples': ai_count,
                'human_samples': human_count,
                'ai_percentage': (ai_count / total_count * 100) if total_count > 0 else 0
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/detector/logs', methods=['GET'])
    def get_training_logs():
        """Получение логов обучения"""
        try:
            limit = request.args.get('limit', 20, type=int)
            training_service = get_training_service()
            
            if training_service:
                logs = training_service.get_training_logs(limit)
                return jsonify({'logs': logs})
            else:
                return jsonify({'logs': []})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/detector/train', methods=['POST'])
    def train_detector():
        """Запуск обучения детектора"""
        try:
            training_service = get_training_service()
            if not training_service:
                return jsonify({'error': 'Сервис обучения недоступен'}), 500
            
            data = request.get_json() or {}
            force = data.get('force', False)
            
            result = training_service.train_model(force)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/detector/predict', methods=['POST'])
    def predict_with_detector():
        """Предсказание с использованием детектора"""
        try:
            data = request.get_json()
            if not data or 'text' not in data:
                return jsonify({'error': 'Текст не предоставлен'}), 400
            
            training_service = get_training_service()
            if not training_service:
                return jsonify({'error': 'Сервис обучения недоступен'}), 500
            
            text = data['text']
            use_hybrid = data.get('use_hybrid', True)
            
            result = training_service.predict_text(text, use_hybrid)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/detector/config', methods=['GET', 'POST'])
    def detector_config():
        """Конфигурация детектора"""
        try:
            training_service = get_training_service()
            if not training_service:
                return jsonify({'error': 'Сервис обучения недоступен'}), 500
            
            if request.method == 'GET':
                status = training_service.get_training_status()
                return jsonify(status)
            else:
                data = request.get_json() or {}
                result = training_service.update_config(data)
                return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500 