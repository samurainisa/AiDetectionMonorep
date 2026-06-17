import os
from app import app
from core.database import init_database

# Инициализация при запуске на продакшене
with app.app_context():
    # Создаем папку для загрузок
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    # Инициализируем БД
    init_database(app)

    # Опционально инициализируем сервис обучения (если зависимости доступны)
    try:
        import os
        from sqlalchemy.engine import url as sa_url
        from core.pangram_client import analyze_text
        from training_service import initialize_training_service

        database_url = os.getenv("DATABASE_URL", "")
        ai_mode = os.getenv("AI_MODE", "pangram_plus_ai").strip().lower()
        if ai_mode not in {"pangram_plus_ai", "pangram_only"}:
            print(f"[WARN] Некорректный AI_MODE='{ai_mode}', используется 'pangram_plus_ai'")
            ai_mode = "pangram_plus_ai"
        sqlite_path = "instance/ai_detection.db"

        # training_service ожидает путь к sqlite-файлу.
        # Для PostgreSQL просто оставляем fallback sqlite-путь.
        if database_url.startswith("sqlite:///"):
            parsed = sa_url.make_url(database_url)
            if parsed.database:
                sqlite_path = parsed.database

        os.environ["AI_MODE"] = ai_mode
        initialize_training_service(sqlite_path, analyze_text)
        print(f"[OK] Режим AI: {ai_mode}")
    except Exception as e:
        print(f"[WARN] Сервис обучения отключен: {e}")

if __name__ == "__main__":
    app.run()