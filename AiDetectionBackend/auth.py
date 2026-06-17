"""
Модуль аутентификации и авторизации пользователей
"""
import jwt
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from core.database import db
from models import User, Role
import re

# Валидация email
def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Валидация пароля
def is_valid_password(password: str) -> bool:
    """Пароль должен содержать минимум 6 символов"""
    return len(password) >= 6

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Хеширует пароль"""
        return generate_password_hash(password)
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Проверяет пароль"""
        return check_password_hash(password_hash, password)
    
    @staticmethod
    def generate_token(user_id: int, role: str) -> str:
        """Генерирует JWT токен"""
        payload = {
            'user_id': user_id,
            'role': role,
            'exp': datetime.utcnow() + timedelta(days=7),  # токен действует 7 дней
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    @staticmethod
    def verify_token(token: str) -> dict:
        """Проверяет JWT токен"""
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            raise Exception("Токен истек")
        except jwt.InvalidTokenError:
            raise Exception("Недействительный токен")
    
    @staticmethod
    def register_user(email: str, password: str, first_name: str, last_name: str, 
                     role: str = 'student', group_id: int = None, student_id: str = None) -> User:
        """Регистрирует нового пользователя"""
        
        # Валидация
        if not is_valid_email(email):
            raise ValueError("Некорректный email адрес")
        
        if not is_valid_password(password):
            raise ValueError("Пароль должен содержать минимум 6 символов")
        
        if not first_name or not last_name:
            raise ValueError("Имя и фамилия обязательны")
        
        # Проверка существования пользователя
        from core.user_database import UserDB
        if UserDB.get_by_email(email):
            raise ValueError("Пользователь с таким email уже существует")
        
        # Создание пользователя
        try:
            role_enum = Role(role)
        except ValueError:
            raise ValueError("Недопустимая роль пользователя")
        
        password_hash = AuthService.hash_password(password)
        
        user = User(
            id=0,  # будет установлен при сохранении
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role_enum,
            group_id=group_id,
            student_id=student_id
        )
        
        # Сохранение в БД
        user_id = UserDB.create_user(user, password_hash)
        user.id = user_id
        
        return user
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> tuple[User, str]:
        """Аутентифицирует пользователя и возвращает пользователя и токен"""
        
        if not email or not password:
            raise ValueError("Email и пароль обязательны")
        
        from core.user_database import UserDB
        user_data = UserDB.get_by_email(email)
        
        if not user_data:
            raise ValueError("Неверный email или пароль")
        
        user, password_hash = user_data
        
        if not AuthService.verify_password(password, password_hash):
            raise ValueError("Неверный email или пароль")
        
        if not user.is_active:
            raise ValueError("Аккаунт заблокирован")
        
        # Обновляем время последнего входа
        user.last_login = datetime.now()
        UserDB.update_last_login(user.id)
        
        # Генерируем токен
        token = AuthService.generate_token(user.id, user.role.value)
        
        return user, token

# Декораторы для проверки авторизации
def token_required(f):
    """Декоратор для проверки JWT токена"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Токен не предоставлен'}), 401
        
        try:
            # Убираем 'Bearer ' если есть
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = AuthService.verify_token(token)
            
            # Получаем пользователя из БД
            from core.user_database import UserDB
            user_data = UserDB.get_by_id(payload['user_id'])
            if not user_data:
                return jsonify({'error': 'Пользователь не найден'}), 401
            
            user = user_data[0]  # UserDB.get_by_id возвращает (user, password_hash)
            
            if not user.is_active:
                return jsonify({'error': 'Аккаунт заблокирован'}), 401
            
            # Добавляем пользователя в контекст запроса
            request.current_user = user
            
        except Exception as e:
            return jsonify({'error': str(e)}), 401
        
        return f(*args, **kwargs)
    
    return decorated

def role_required(*allowed_roles):
    """Декоратор для проверки роли пользователя"""
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            user = request.current_user
            
            if user.role.value not in allowed_roles:
                return jsonify({'error': 'Недостаточно прав доступа'}), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator

def get_current_user():
    """Получает текущего пользователя из контекста запроса"""
    return getattr(request, 'current_user', None)

# Функции для работы с группами и правами доступа
def can_view_detection(user: User, detection_user_id: int, detection_group_id: int = None) -> bool:
    """Проверяет, может ли пользователь просматривать детекцию"""
    
    # Админы могут все
    if user.role == Role.ADMIN:
        return True
    
    # Пользователь может видеть свои детекции
    if user.id == detection_user_id:
        return True
    
    # Преподаватели могут видеть детекции студентов из своих групп
    if user.role == Role.TEACHER and detection_group_id:
        # TODO: Добавить проверку принадлежности группы к преподавателю
        return True
    
    return False

def can_view_analytics(user: User) -> bool:
    """Проверяет, может ли пользователь просматривать аналитику"""
    return user.role in [Role.TEACHER, Role.ADMIN, Role.DEVELOPER]

def can_manage_users(user: User) -> bool:
    """Проверяет, может ли пользователь управлять пользователями"""
    return user.role in [Role.ADMIN, Role.DEVELOPER]

# Вспомогательные функции
def get_user_permissions(user: User) -> dict:
    """Возвращает разрешения пользователя"""
    return {
        'can_view_analytics': can_view_analytics(user),
        'can_manage_users': can_manage_users(user),
        'is_teacher': user.is_teacher(),
        'is_student': user.is_student(),
        'is_admin': user.role == Role.ADMIN,
        'is_developer': user.role == Role.DEVELOPER
    }

def sanitize_user_data(user: User) -> dict:
    """Возвращает безопасные данные пользователя для API"""
    return {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.get_full_name(),
        'role': user.role.value,
        'group_id': user.group_id,
        'student_id': user.student_id,
        'is_active': user.is_active,
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'permissions': get_user_permissions(user)
    }