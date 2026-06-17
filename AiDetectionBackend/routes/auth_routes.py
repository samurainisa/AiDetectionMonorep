"""
Маршруты для аутентификации и авторизации
"""
from flask import Blueprint, request, jsonify, current_app
from auth import AuthService, token_required, role_required, get_current_user, sanitize_user_data
from models import Role

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400
        
        # Извлекаем данные
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        role = data.get('role', 'student').lower()
        group_id = data.get('group_id')
        student_id = data.get('student_id', '').strip()
        
        # Регистрируем пользователя
        user = AuthService.register_user(
            email=email,
            password=password, 
            first_name=first_name,
            last_name=last_name,
            role=role,
            group_id=group_id,
            student_id=student_id
        )
        
        # Генерируем токен
        token = AuthService.generate_token(user.id, user.role.value)
        
        return jsonify({
            'message': 'Пользователь успешно зарегистрирован',
            'user': sanitize_user_data(user),
            'token': token
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Вход пользователя"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Аутентифицируем пользователя
        user, token = AuthService.authenticate_user(email, password)
        
        return jsonify({
            'message': 'Успешный вход',
            'user': sanitize_user_data(user),
            'token': token
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user_info():
    """Получение информации о текущем пользователе"""
    try:
        user = get_current_user()
        return jsonify({
            'user': sanitize_user_data(user)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/refresh', methods=['POST'])
@token_required 
def refresh_token():
    """Обновление JWT токена"""
    try:
        user = get_current_user()
        new_token = AuthService.generate_token(user.id, user.role.value)
        
        return jsonify({
            'token': new_token,
            'user': sanitize_user_data(user)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """Выход пользователя (в текущей реализации просто подтверждение)"""
    try:
        return jsonify({'message': 'Успешный выход'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Административные маршруты
@auth_bp.route('/users', methods=['GET'])
@role_required('admin', 'teacher')
def get_users():
    """Получение списка пользователей (только для админов и преподавателей)"""
    try:
        current_user = get_current_user()
        
        # Параметры пагинации
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        role_filter = request.args.get('role')
        group_filter = request.args.get('group_id', type=int)
        
        from core.user_database import UserDB
        users_data = UserDB.get_users_list(
            page=page,
            per_page=per_page,
            role_filter=role_filter,
            group_filter=group_filter,
            current_user_role=current_user.role.value
        )
        
        return jsonify(users_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/users/<int:user_id>', methods=['GET'])
@role_required('admin', 'teacher')
def get_user_details(user_id):
    """Получение детальной информации о пользователе"""
    try:
        from core.user_database import UserDB
        user_data = UserDB.get_by_id(user_id)
        
        if not user_data:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        user = user_data[0]
        return jsonify({
            'user': sanitize_user_data(user)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/users/<int:user_id>/toggle-active', methods=['PUT'])
@role_required('admin')
def toggle_user_active(user_id):
    """Активация/деактивация пользователя (только для админов)"""
    try:
        from core.user_database import UserDB
        success = UserDB.toggle_user_active(user_id)
        
        if not success:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        return jsonify({'message': 'Статус пользователя изменен'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Маршруты для работы с группами
@auth_bp.route('/groups', methods=['GET'])
@role_required('admin', 'teacher')
def get_groups():
    """Получение списка групп"""
    try:
        from core.user_database import GroupDB
        groups = GroupDB.get_all_groups()
        
        return jsonify({
            'groups': [group.__dict__ for group in groups]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/groups', methods=['POST'])
@role_required('admin')
def create_group():
    """Создание новой группы (только для админов)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400
        
        name = data.get('name', '').strip()
        course_code = data.get('course_code', '').strip()
        academic_year = data.get('academic_year', '').strip()
        
        if not all([name, course_code, academic_year]):
            return jsonify({'error': 'Все поля обязательны'}), 400
        
        from core.user_database import GroupDB
        from models import Group
        
        group = Group(
            id=0,  # будет установлен при сохранении
            name=name,
            course_code=course_code,
            academic_year=academic_year
        )
        
        group_id = GroupDB.create_group(group)
        group.id = group_id
        
        return jsonify({
            'message': 'Группа создана',
            'group': group.__dict__
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def register_auth_routes(app):
    """Регистрирует маршруты авторизации в приложении"""
    app.register_blueprint(auth_bp)