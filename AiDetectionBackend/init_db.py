#!/usr/bin/env python3
"""
Инициализация PostgreSQL:
1) Создаёт БД, если её нет
2) Создаёт таблицы через SQLAlchemy

Запуск (Windows PowerShell):
  $env:DATABASE_URL = "postgresql://postgres:password@localhost:5432/ai_detection"
  python AiDetectionBackend/init_db.py
"""

import os
import psycopg2
from sqlalchemy.engine import url as sa_url

from app import app
from core.database import init_database, db
from core.user_database import init_user_database


def ensure_database_exists(database_url: str) -> None:
    parsed = sa_url.make_url(database_url)
    dbname = parsed.database
    user = parsed.username or 'postgres'
    password = parsed.password or ''
    host = parsed.host or 'localhost'
    port = parsed.port or 5432

    # Подключаемся к postgres (системная БД) и создаём целевую при отсутствии
    conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host, port=port)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
    exists = cur.fetchone() is not None
    if not exists:
        cur.execute(f'CREATE DATABASE "{dbname}"')
        print(f"[OK] Создана БД: {dbname}")
    else:
        print(f"[OK] БД уже существует: {dbname}")
    cur.close()
    conn.close()


def main() -> None:
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise RuntimeError('DATABASE_URL не задан. Укажи, например: postgresql://postgres:password@localhost:5432/ai_detection')

    print(f"[INFO] DATABASE_URL={database_url}")
    ensure_database_exists(database_url)

    with app.app_context():
        # Создаём таблицы
        init_database(app)
        db.create_all()
        init_user_database()
        print("[OK] Все таблицы созданы/актуализированы в PostgreSQL")


if __name__ == "__main__":
    main()


