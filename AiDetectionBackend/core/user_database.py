"""
Расширение базы данных для работы с пользователями
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from core.database import db
from models import User, Group, Role
from typing import Optional, List, Tuple

# Модели SQLAlchemy для пользователей
class UserModel(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='student')
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    student_id = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Связи
    group = db.relationship('GroupModel', backref='users', lazy=True)
    detections = db.relationship('DetectionModel', backref='user', lazy=True)

class GroupModel(db.Model):
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_code = db.Column(db.String(50), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.Integer, nullable=True)
    faculty = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DetectionModel(db.Model):
    __tablename__ = 'user_detections'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    original_detection_id = db.Column(db.Integer, nullable=False)  # ссылка на Detection из старой таблицы
    document_category = db.Column(db.String(50), nullable=True)
    assignment_name = db.Column(db.String(200), nullable=True)
    subject = db.Column(db.String(100), nullable=True)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Класс для работы с пользователями
class UserDB:
    
    @staticmethod
    def create_user(user: User, password_hash: str) -> int:
        """Создает нового пользователя и возвращает его ID"""
        try:
            user_model = UserModel(
                email=user.email,
                password_hash=password_hash,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role.value,
                group_id=user.group_id,
                student_id=user.student_id,
                is_active=user.is_active
            )
            
            db.session.add(user_model)
            db.session.commit()
            
            return user_model.id
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Ошибка создания пользователя: {str(e)}")
    
    @staticmethod
    def get_by_email(email: str) -> Optional[Tuple[User, str]]:
        """Получает пользователя по email, возвращает (User, password_hash) или None"""
        try:
            user_model = UserModel.query.filter_by(email=email.lower()).first()
            if not user_model:
                return None
            
            user = UserDB._model_to_user(user_model)
            return (user, user_model.password_hash)
            
        except Exception as e:
            print(f"Ошибка получения пользователя: {e}")
            return None
    
    @staticmethod
    def get_by_id(user_id: int) -> Optional[Tuple[User, str]]:
        """Получает пользователя по ID"""
        try:
            user_model = UserModel.query.get(user_id)
            if not user_model:
                return None
            
            user = UserDB._model_to_user(user_model)
            return (user, user_model.password_hash)
            
        except Exception as e:
            print(f"Ошибка получения пользователя: {e}")
            return None
    
    @staticmethod
    def update_last_login(user_id: int) -> bool:
        """Обновляет время последнего входа"""
        try:
            user_model = UserModel.query.get(user_id)
            if user_model:
                user_model.last_login = datetime.utcnow()
                db.session.commit()
                return True
            return False
            
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка обновления времени входа: {e}")
            return False
    
    @staticmethod
    def toggle_user_active(user_id: int) -> bool:
        """Переключает активность пользователя"""
        try:
            user_model = UserModel.query.get(user_id)
            if user_model:
                user_model.is_active = not user_model.is_active
                db.session.commit()
                return True
            return False
            
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка изменения статуса пользователя: {e}")
            return False
    
    @staticmethod
    def get_users_list(page: int = 1, per_page: int = 20, role_filter: str = None, 
                      group_filter: int = None, current_user_role: str = 'student') -> dict:
        """Получает список пользователей с пагинацией и фильтрацией"""
        try:
            query = UserModel.query
            
            # Фильтрация по роли
            if role_filter:
                query = query.filter(UserModel.role == role_filter)
            
            # Фильтрация по группе
            if group_filter:
                query = query.filter(UserModel.group_id == group_filter)
            
            # Преподаватели видят только студентов своих групп (упрощенная логика)
            if current_user_role == 'teacher':
                query = query.filter(UserModel.role == 'student')
            
            # Пагинация
            users_paginated = query.order_by(UserModel.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            users_list = []
            for user_model in users_paginated.items:
                user_data = {
                    'id': user_model.id,
                    'email': user_model.email,
                    'first_name': user_model.first_name,
                    'last_name': user_model.last_name,
                    'full_name': f"{user_model.first_name} {user_model.last_name}",
                    'role': user_model.role,
                    'group_id': user_model.group_id,
                    'student_id': user_model.student_id,
                    'is_active': user_model.is_active,
                    'created_at': user_model.created_at.isoformat(),
                    'last_login': user_model.last_login.isoformat() if user_model.last_login else None
                }
                
                # Добавляем информацию о группе
                if user_model.group:
                    user_data['group_name'] = user_model.group.name
                    user_data['course_code'] = user_model.group.course_code
                
                users_list.append(user_data)
            
            return {
                'users': users_list,
                'total': users_paginated.total,
                'pages': users_paginated.pages,
                'current_page': page,
                'per_page': per_page
            }
            
        except Exception as e:
            print(f"Ошибка получения списка пользователей: {e}")
            return {
                'users': [],
                'total': 0,
                'pages': 0,
                'current_page': page,
                'per_page': per_page
            }
    
    @staticmethod
    def _model_to_user(user_model: UserModel) -> User:
        """Конвертирует UserModel в User"""
        try:
            role = Role(user_model.role) if user_model.role in [r.value for r in Role] else Role.STUDENT
        except ValueError:
            role = Role.STUDENT  # По умолчанию
        
        user = User(
            id=user_model.id,
            email=user_model.email,
            first_name=user_model.first_name,
            last_name=user_model.last_name,
            role=role,
            group_id=user_model.group_id,
            student_id=user_model.student_id
        )
        
        user.is_active = user_model.is_active
        user.created_at = user_model.created_at
        user.last_login = user_model.last_login
        
        return user

# Класс для работы с группами
class GroupDB:
    
    @staticmethod
    def create_group(group: Group) -> int:
        """Создает новую группу"""
        try:
            group_model = GroupModel(
                name=group.name,
                course_code=group.course_code,
                academic_year=group.academic_year,
                semester=group.semester,
                faculty=group.faculty
            )
            
            db.session.add(group_model)
            db.session.commit()
            
            return group_model.id
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Ошибка создания группы: {str(e)}")
    
    @staticmethod
    def get_all_groups() -> List[Group]:
        """Получает все группы"""
        try:
            group_models = GroupModel.query.order_by(GroupModel.name).all()
            
            groups = []
            for model in group_models:
                group = Group(
                    id=model.id,
                    name=model.name,
                    course_code=model.course_code,
                    academic_year=model.academic_year
                )
                group.semester = model.semester
                group.faculty = model.faculty
                group.created_at = model.created_at
                groups.append(group)
            
            return groups
            
        except Exception as e:
            print(f"Ошибка получения групп: {e}")
            return []
    
    @staticmethod
    def get_by_id(group_id: int) -> Optional[Group]:
        """Получает группу по ID"""
        try:
            model = GroupModel.query.get(group_id)
            if not model:
                return None
            
            group = Group(
                id=model.id,
                name=model.name,
                course_code=model.course_code,
                academic_year=model.academic_year
            )
            group.semester = model.semester
            group.faculty = model.faculty
            group.created_at = model.created_at
            
            return group
            
        except Exception as e:
            print(f"Ошибка получения группы: {e}")
            return None

def init_user_database():
    """Инициализирует таблицы пользователей"""
    try:
        db.create_all()
        print("[OK] Таблицы пользователей инициализированы")
        
        # Создаем первого администратора если его нет
        admin = UserModel.query.filter_by(role='admin').first()
        if not admin:
            from auth import AuthService
            
            admin_user = UserModel(
                email='admin@aidetection.local',
                password_hash=AuthService.hash_password('admin123'),
                first_name='Администратор',
                last_name='Системы',
                role='admin',
                is_active=True
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("[OK] Создан администратор: admin@aidetection.local / admin123")
        
    except Exception as e:
        print(f"[ERROR] Ошибка инициализации пользовательских таблиц: {e}")
        db.session.rollback()