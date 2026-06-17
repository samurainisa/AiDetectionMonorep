import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    def _req(name: str) -> str:
        v = os.environ.get(name)
        if not v:
            raise RuntimeError(f"ENV переменная {name} не задана")
        return v

    SECRET_KEY = _req('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = _req('DATABASE_URL')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 32 * 1024 * 1024))
    
    PANGRAM_API_KEY = os.environ.get('PANGRAM_API_KEY')
    
    PLAGIARISM_ENABLED = os.environ.get('PLAGIARISM_ENABLED', 'true').lower() == 'true'
    PLAGIARISM_DB_HOST = os.environ.get('PLAGIARISM_DB_HOST', 'localhost')
    PLAGIARISM_DB_PORT = int(os.environ.get('PLAGIARISM_DB_PORT', 5432))
    PLAGIARISM_DB_NAME = os.environ.get('PLAGIARISM_DB_NAME', 'plagiarism_db')
    PLAGIARISM_DB_USER = os.environ.get('PLAGIARISM_DB_USER', 'postgres')
    PLAGIARISM_DB_PASSWORD = os.environ.get('PLAGIARISM_DB_PASSWORD', '')
