"""
Маршруты для генерации отчетов
"""
from flask import Blueprint, request, jsonify, current_app, make_response
from auth import token_required
import io
import json
from datetime import datetime

# Импорты для PDF
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    
    # Регистрируем современные шрифты DejaVu Sans для поддержки русского языка
    try:
        import os
        font_dir = os.path.join(os.path.dirname(__file__), '..', 'fonts')
        
        # Регистрируем шрифты DejaVu Sans
        dejavu_regular = os.path.join(font_dir, 'DejaVuSans.ttf')
        dejavu_bold = os.path.join(font_dir, 'DejaVuSans-Bold.ttf') 
        dejavu_oblique = os.path.join(font_dir, 'DejaVuSans-Oblique.ttf')
        
        if os.path.exists(dejavu_regular):
            pdfmetrics.registerFont(TTFont('DejaVuSans', dejavu_regular))
            DEFAULT_FONT = 'DejaVuSans'
            print(f"[INFO] Registered DejaVu Sans Regular font: {dejavu_regular}")
        else:
            raise FileNotFoundError("DejaVu Sans font not found")
            
        if os.path.exists(dejavu_bold):
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', dejavu_bold))
            DEFAULT_FONT_BOLD = 'DejaVuSans-Bold'
            print(f"[INFO] Registered DejaVu Sans Bold font: {dejavu_bold}")
        else:
            DEFAULT_FONT_BOLD = DEFAULT_FONT
            
        if os.path.exists(dejavu_oblique):
            pdfmetrics.registerFont(TTFont('DejaVuSans-Oblique', dejavu_oblique))
            DEFAULT_FONT_ITALIC = 'DejaVuSans-Oblique'
            print(f"[INFO] Registered DejaVu Sans Oblique font: {dejavu_oblique}")
        else:
            DEFAULT_FONT_ITALIC = DEFAULT_FONT
            
    except Exception as e:
        print(f"[WARN] Could not register DejaVu Sans fonts: {e}")
        # Fallback к стандартному шрифту
        try:
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
            DEFAULT_FONT = 'STSong-Light'
            DEFAULT_FONT_BOLD = 'STSong-Light'
            DEFAULT_FONT_ITALIC = 'STSong-Light'
        except:
            DEFAULT_FONT = 'Helvetica'
            DEFAULT_FONT_BOLD = 'Helvetica-Bold'
            DEFAULT_FONT_ITALIC = 'Helvetica-Oblique'
    
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("[WARN] ReportLab not installed. PDF generation will be unavailable.")

report_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

def create_pdf_buffer():
    """Создает буфер для PDF"""
    return io.BytesIO()

def escape_for_pdf(text):
    """Экранирует текст для безопасного использования в PDF"""
    if not text:
        return ''
    
    # Заменяем проблемные символы
    text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#x27;')
    
    # Обрезаем слишком длинный текст
    if len(text) > 500:
        text = text[:497] + "..."
    
    return text

def add_pdf_header(story, title):
    """Добавляет красивый заголовок к PDF"""
    styles = getSampleStyleSheet()
    
    # Современный заголовок с градиентом
    title_style = ParagraphStyle(
        'ModernTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        spaceBefore=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a365d'),  # Темно-синий
        fontName=DEFAULT_FONT_BOLD if 'DEFAULT_FONT_BOLD' in globals() else DEFAULT_FONT,
        leading=28
    )
    
    # Подзаголовок
    subtitle_style = ParagraphStyle(
        'ModernSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4a5568'),  # Серый
        fontName=DEFAULT_FONT,
        leading=15
    )
    
    # Экранируем специальные символы для ReportLab
    safe_title = escape_for_pdf(title)
    story.append(Paragraph(safe_title, title_style))
    story.append(Paragraph("Автоматически сгенерированный отчет системы AI Detection", subtitle_style))
    
    # Добавляем разделительную линию
    from reportlab.platypus import HRFlowable
    story.append(HRFlowable(width="100%", thickness=2, lineCap='round', color=colors.HexColor('#e2e8f0')))
    story.append(Spacer(1, 20))

def add_detection_info(story, detection_data):
    """Добавляет современную информацию о детекции"""
    styles = getSampleStyleSheet()
    
    # Современный заголовок секции
    heading_style = ParagraphStyle(
        'ModernHeading2',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2d3748'),
        fontName=DEFAULT_FONT_BOLD if 'DEFAULT_FONT_BOLD' in globals() else DEFAULT_FONT,
        spaceAfter=15,
        spaceBefore=10  
    )
    story.append(Paragraph("Информация о документе", heading_style))
    
    # Современная таблица с улучшенным дизайном
    data = [
        ['Параметр', 'Значение'],
        ['Имя файла', escape_for_pdf(detection_data.get('filename', 'N/A'))],
        ['Тип файла', escape_for_pdf(detection_data.get('file_type', 'N/A'))],
        ['Размер текста', f"{detection_data.get('text_length', 0)} слов"],
        ['Дата анализа', escape_for_pdf(detection_data.get('created_at', 'N/A'))],
    ]
    
    table = Table(data, colWidths=[2.5*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),  # Синий заголовок
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), DEFAULT_FONT_BOLD if 'DEFAULT_FONT_BOLD' in globals() else DEFAULT_FONT),
        ('FONTNAME', (0, 1), (-1, -1), DEFAULT_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),  # Светло-серый фон
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),  # Тонкие серые границы
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white])  # Чередующиеся строки
    ]))
    
    story.append(table)
    story.append(Spacer(1, 25))

def add_ai_analysis(story, detection_data):
    """Добавляет современные результаты AI анализа"""
    styles = getSampleStyleSheet()
    
    # Современный заголовок секции
    heading_style = ParagraphStyle(
        'ModernHeading2',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2d3748'),
        fontName=DEFAULT_FONT_BOLD if 'DEFAULT_FONT_BOLD' in globals() else DEFAULT_FONT,
        spaceAfter=15,
        spaceBefore=10
    )
    story.append(Paragraph(" Анализ на ИИ", heading_style))
    
    # Безопасные значения (коэрция None -> 0)
    def to_float(value):
        try:
            return float(value) if value is not None else 0.0
        except Exception:
            return 0.0

    ai_likelihood = to_float(detection_data.get('ai_likelihood'))
    prediction = detection_data.get('prediction', 'N/A')
    max_ai = to_float(detection_data.get('max_ai_likelihood'))
    avg_ai = to_float(detection_data.get('avg_ai_likelihood'))
    
    # Данные анализа
    ai_data = [
        ['Метрика', 'Значение'],
        ['Вероятность ИИ', f"{ai_likelihood * 100:.1f}%"],
        ['Предсказание', escape_for_pdf(prediction)],
        ['Максимальная вероятность', f"{max_ai * 100:.1f}%"],
        ['Средняя вероятность', f"{avg_ai * 100:.1f}%"],
    ]
    
    if 'skip_reason' in detection_data:
        ai_data.append(['Причина пропуска анализа', escape_for_pdf(detection_data['skip_reason'])])
    
    ai_table = Table(ai_data, colWidths=[2.5*inch, 3.5*inch])
    
    # Выбираем цвет в зависимости от вероятности ИИ
    if ai_likelihood >= 0.8:
        header_color = colors.HexColor('#dc2626')  # Красный - высокая вероятность
        bg_color = colors.HexColor('#fef2f2')
    elif ai_likelihood >= 0.5:
        header_color = colors.HexColor('#d97706')  # Оранжевый - средняя вероятность
        bg_color = colors.HexColor('#fffbeb')
    elif ai_likelihood >= 0.2:
        header_color = colors.HexColor('#0891b2')  # Синий - низкая вероятность
        bg_color = colors.HexColor('#f0f9ff')
    else:
        header_color = colors.HexColor('#059669')  # Зеленый - очень низкая вероятность
        bg_color = colors.HexColor('#f0fdf4')
    
    ai_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), DEFAULT_FONT_BOLD if 'DEFAULT_FONT_BOLD' in globals() else DEFAULT_FONT),
        ('FONTNAME', (0, 1), (-1, -1), DEFAULT_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, -1), bg_color),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [bg_color, colors.white])
    ]))
    
    story.append(ai_table)
    story.append(Spacer(1, 25))

def add_plagiarism_analysis(story, plagiarism_data):
    """Добавляет современные результаты анализа плагиата"""
    styles = getSampleStyleSheet()
    
    # Современный заголовок секции
    heading_style = ParagraphStyle(
        'ModernHeading2',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2d3748'),
        fontName=DEFAULT_FONT_BOLD if 'DEFAULT_FONT_BOLD' in globals() else DEFAULT_FONT,
        spaceAfter=15,
        spaceBefore=10
    )
    normal_style = ParagraphStyle(
        'ModernNormal',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT,
        fontSize=10
    )
    
    story.append(Paragraph("🔍 Анализ на плагиат", heading_style))
    
    if not plagiarism_data:
        story.append(Paragraph("Данные о плагиате недоступны", normal_style))
        return
    
    # Общая статистика плагиата
    originality = plagiarism_data.get('originality_percentage', 100)
    similarity = 100 - originality
    
    plag_data = [
        ['Метрика', 'Значение'],
        ['Оригинальность', f"{originality:.1f}%"],
        ['Схожесть', f"{similarity:.1f}%"],
        ['Уровень плагиата', escape_for_pdf(plagiarism_data.get('plagiarism_level', 'Не определен'))],
        ['Количество совпадений', str(plagiarism_data.get('matches_count', 0))],
    ]
    
    # Выбираем цвет в зависимости от уровня плагиата
    if similarity >= 80:
        header_color = colors.HexColor('#dc2626')  # Красный - высокий плагиат
        bg_color = colors.HexColor('#fef2f2')
    elif similarity >= 60:
        header_color = colors.HexColor('#d97706')  # Оранжевый - средний плагиат
        bg_color = colors.HexColor('#fffbeb')
    elif similarity >= 20:
        header_color = colors.HexColor('#eab308')  # Желтый - низкий плагиат
        bg_color = colors.HexColor('#fefce8')
    else:
        header_color = colors.HexColor('#059669')  # Зеленый - оригинал
        bg_color = colors.HexColor('#f0fdf4')
    
    plag_table = Table(plag_data, colWidths=[2.5*inch, 3.5*inch])
    plag_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), DEFAULT_FONT_BOLD if 'DEFAULT_FONT_BOLD' in globals() else DEFAULT_FONT),
        ('FONTNAME', (0, 1), (-1, -1), DEFAULT_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, -1), bg_color),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [bg_color, colors.white])
    ]))
    
    story.append(plag_table)
    story.append(Spacer(1, 25))

@report_bp.route('/detection/<int:detection_id>/pdf', methods=['GET'])
@token_required
def generate_detection_pdf_report(detection_id):
    """Генерирует PDF отчет для детекции"""
    if not PDF_AVAILABLE:
        return jsonify({'error': 'PDF generation not available'}), 503
    
    try:
        # Получаем данные детекции
        from core.database import Detection
        detection = Detection.query.get_or_404(detection_id)
        
        # Получаем данные о плагиате
        plagiarism_data = None
        try:
            from plagiarism_engine import plagiarism_engine
            report = plagiarism_engine.get_report(detection_id)
            if report:
                plagiarism_data = report.to_dict()
        except Exception as e:
            print(f"[WARN] Could not get plagiarism data: {e}")
        
        # Создаем PDF буфер
        buffer = create_pdf_buffer()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Добавляем контент
        add_pdf_header(story, f"Отчет об анализе документа: {detection.filename}")
        
        # Информация о документе
        detection_data = {
            'filename': detection.filename,
            'file_type': detection.file_type,
            'text_length': detection.text_length,
            'created_at': detection.created_at.strftime('%d.%m.%Y %H:%M'),
            'ai_likelihood': detection.ai_likelihood,
            'prediction': detection.prediction,
            'max_ai_likelihood': detection.max_ai_likelihood,
            'avg_ai_likelihood': detection.avg_ai_likelihood,
        }
        
        # Проверяем, был ли пропущен анализ из-за плагиата
        try:
            full_response = json.loads(detection.full_response) if detection.full_response else {}
            if full_response.get('skip_reason'):
                detection_data['skip_reason'] = full_response['skip_reason']
        except:
            pass
        
        add_detection_info(story, detection_data)
        add_ai_analysis(story, detection_data)
        
        if plagiarism_data:
            add_plagiarism_analysis(story, plagiarism_data)
        
        # Добавляем footer
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle('RussianNormal', parent=styles['Normal'], fontName=DEFAULT_FONT)
        
        story.append(Spacer(1, 50))
        story.append(Paragraph(
            f"Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            normal_style
        ))
        story.append(Paragraph(
            "AI Detection System",
            normal_style
        ))
        
        # Генерируем PDF
        doc.build(story)
        buffer.seek(0)
        
        # Создаем ответ
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="detection_report_{detection_id}.pdf"'
        
        return response
        
    except Exception as e:
        print(f"[ERROR] PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Ошибка генерации PDF отчета'}), 500

@report_bp.route('/plagiarism/<int:detection_id>/pdf', methods=['GET'])
@token_required
def generate_plagiarism_pdf_report(detection_id):
    """Генерирует PDF отчет о плагиате"""
    if not PDF_AVAILABLE:
        return jsonify({'error': 'PDF generation not available'}), 503
    
    try:
        print(f"[DEBUG] Starting PDF generation for detection {detection_id}")
        
        # Получаем данные детекции и плагиата (с fallback в БД)
        from core.database import Detection, PlagiarismCheck
        from plagiarism_engine import plagiarism_engine
        
        detection = Detection.query.get_or_404(detection_id)
        print(f"[DEBUG] Found detection: {detection.filename}")
        
        # Сначала пробуем из БД, затем из in-memory
        report_dict = None
        try:
            pc = PlagiarismCheck.query.filter_by(detection_id=detection_id).order_by(PlagiarismCheck.created_at.desc()).first()
        except Exception as e:
            pc = None
            print(f"[WARN] DB read failed: {e}")
        if pc:
            import json as _json
            try:
                matches_list = _json.loads(pc.matches_json or '[]')
            except Exception:
                matches_list = []
            try:
                similar_documents_list = _json.loads(pc.similar_documents_json or '[]')
            except Exception:
                similar_documents_list = []
            report_dict = {
                'detection_id': detection_id,
                'total_similarity_score': None,
                'plagiarism_level': pc.plagiarism_level or 'original',
                'originality_percentage': pc.originality_percentage or 100.0,
                'total_fragments': pc.total_fragments or 0,
                'matched_fragments': pc.matched_fragments or 0,
                'matches': matches_list,
                'similar_documents': similar_documents_list
            }
        else:
            _report_obj = plagiarism_engine.get_report(detection_id)
            if _report_obj:
                print(f"[DEBUG] Found plagiarism report (in-memory)")
                report_dict = _report_obj.to_dict()
            else:
                print(f"[WARN] No plagiarism report found for detection {detection_id}")
                return jsonify({'error': 'Отчет о плагиате не найден'}), 404
        
        # Создаем простой PDF для тестирования
        buffer = create_pdf_buffer()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        styles = getSampleStyleSheet()
        story = []
        
        # Создаем современные стили
        title_style = ParagraphStyle(
            'ModernTitle', 
            parent=styles['Title'],
            fontName=DEFAULT_FONT_BOLD if 'DEFAULT_FONT_BOLD' in globals() else DEFAULT_FONT,
            fontSize=20,
            textColor=colors.HexColor('#1a365d'),
            alignment=TA_CENTER,
            spaceAfter=10
        )
        
        subtitle_style = ParagraphStyle(
            'ModernSubtitle',
            parent=styles['Normal'],
            fontName=DEFAULT_FONT,
            fontSize=11,
            textColor=colors.HexColor('#4a5568'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        heading_style = ParagraphStyle(
            'ModernHeading',
            parent=styles['Heading2'],
            fontName=DEFAULT_FONT_BOLD if 'DEFAULT_FONT_BOLD' in globals() else DEFAULT_FONT,
            fontSize=14,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=10
        )
        
        normal_style = ParagraphStyle(
            'ModernNormal',
            parent=styles['Normal'],
            fontName=DEFAULT_FONT,
            fontSize=10,
            textColor=colors.HexColor('#2d3748')
        )
        
        # Красивый заголовок с иконкой
        title = f" Отчет о плагиате"
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(f"Документ: {escape_for_pdf(detection.filename)}", subtitle_style))
        
        # Разделительная линия
        from reportlab.platypus import HRFlowable
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        story.append(Spacer(1, 15))
        
        # Информация о плагиате в красивой таблице
        # Перепроверка оригинальности на основе matches, если явно противоречит
        try:
            matches = report_dict.get('matches', []) or []
            originality = float(report_dict.get('originality_percentage', 100))
            if matches and (originality >= 99.9 or originality is None):
                by_pos = {}
                for m in matches:
                    pos = m.get('target_fragment_pos')
                    s = float(m.get('similarity_score', 0) or 0)
                    by_pos.setdefault(pos, []).append(s)
                totals = [max(v) for v in by_pos.values() if v]
                sim = sum(totals) / len(totals) if totals else 0.0
                originality = max(0.0, 100.0 - sim * 100.0)
                report_dict['originality_percentage'] = originality
        except Exception:
            originality = report_dict.get('originality_percentage', 100)
        similarity = 100 - originality
        
        # Выбираем цвет в зависимости от уровня плагиата
        if similarity >= 80:
            result_color = colors.HexColor('#dc2626')  # Красный
            bg_color = colors.HexColor('#fef2f2')
            status = "ВЫСОКИЙ ПЛАГИАТ"
        elif similarity >= 60:
            result_color = colors.HexColor('#d97706')  # Оранжевый
            bg_color = colors.HexColor('#fffbeb')
            status = "СРЕДНИЙ ПЛАГИАТ"
        elif similarity >= 20:
            result_color = colors.HexColor('#eab308')  # Желтый
            bg_color = colors.HexColor('#fefce8')
            status = "НИЗКИЙ ПЛАГИАТ"
        else:
            result_color = colors.HexColor('#059669')  # Зеленый
            bg_color = colors.HexColor('#f0fdf4')
            status = "ОРИГИНАЛ"
        
        # Создаем данные для таблицы результатов
        result_data = [
            ['Результат проверки', status],
            ['Оригинальность', f"{originality:.1f}%"],
            ['Схожесть', f"{similarity:.1f}%"],
            ['Найдено совпадений', str(len(report_dict.get('matches', [])))],
            ['Дата проверки', detection.created_at.strftime('%d.%m.%Y %H:%M')]
        ]
        
        result_table = Table(result_data, colWidths=[2.5*inch, 3*inch])
        result_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), result_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), DEFAULT_FONT_BOLD if 'DEFAULT_FONT_BOLD' in globals() else DEFAULT_FONT),
            ('FONTNAME', (0, 1), (-1, -1), DEFAULT_FONT),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), bg_color),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        
        story.append(result_table)
        
        # Footer с логотипом
        story.append(Spacer(1, 40))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        story.append(Spacer(1, 10))
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontName=DEFAULT_FONT,
            fontSize=9,
            textColor=colors.HexColor('#6b7280'),
            alignment=TA_CENTER
        )
        
        story.append(Paragraph(
            f"Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')} | AI Detection System v2.0",
            footer_style
        ))
        
        print(f"[DEBUG] Building PDF...")
        
        # Генерируем PDF
        doc.build(story)
        buffer.seek(0)
        
        print(f"[DEBUG] PDF generated successfully, size: {len(buffer.getvalue())} bytes")
        
        # Создаем ответ
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="plagiarism_report_{detection_id}.pdf"'
        
        return response
        
    except Exception as e:
        print(f"[ERROR] PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Ошибка генерации PDF отчета: {str(e)}'}), 500

def register_report_routes(app):
    """Регистрирует маршруты отчетов в приложении"""
    app.register_blueprint(report_bp)