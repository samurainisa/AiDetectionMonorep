"""
Обработка файлов и извлечение текста
"""
import PyPDF2
from docx import Document

# Разрешенные расширения файлов
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt'}

def allowed_file(filename: str) -> bool:
    """Проверка разрешенных расширений файлов"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path: str) -> str:
    """Извлечение текста из PDF файла с защитой от дублирования"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            pages_text = []
            seen_pages = set()
            
            for page in pdf_reader.pages:
                page_text = page.extract_text().strip()
                if page_text:
                    # Нормализуем текст для проверки дублирования
                    normalized = ' '.join(page_text.split()).lower()
                    
                    # Добавляем только уникальные страницы
                    if normalized not in seen_pages:
                        pages_text.append(page_text)
                        seen_pages.add(normalized)
            
            result = '\n\n'.join(pages_text)
            return result
            
    except Exception as e:
        raise Exception(f"Ошибка при извлечении текста из PDF: {str(e)}")

def extract_text_from_docx(file_path: str) -> str:
    """Извлечение текста из DOCX файла"""
    try:
        document = Document(file_path)
        
        lines = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]
        
        full_text = "".join(lines)
        return full_text
        
    except Exception as e:
        raise Exception(f"Ошибка при извлечении текста из DOCX: {str(e)}")

def extract_text_from_txt(file_path: str) -> str:
    """Извлечение текста из TXT файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except UnicodeDecodeError:
        # Попробуем другие кодировки
        encodings = ['cp1251', 'latin-1', 'ascii']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read().strip()
            except UnicodeDecodeError:
                continue
        raise Exception("Не удалось определить кодировку файла")
    except Exception as e:
        raise Exception(f"Ошибка при чтении TXT файла: {str(e)}")

def extract_text_from_file(file_path: str, file_type: str) -> str:
    """Общая функция для извлечения текста из файла"""
    if file_type.lower() == 'pdf':
        return extract_text_from_pdf(file_path)
    elif file_type.lower() in ['docx', 'doc']:
        return extract_text_from_docx(file_path)
    elif file_type.lower() == 'txt':
        return extract_text_from_txt(file_path)
    else:
        raise Exception(f"Неподдерживаемый тип файла: {file_type}") 