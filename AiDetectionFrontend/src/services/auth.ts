import axios from 'axios'
import type { AxiosResponse } from 'axios'

// Конфигурация API
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'

// Типы данных
export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: 'student' | 'teacher' | 'admin' | 'developer'
  group_id?: number
  student_id?: string
  is_active: boolean
  last_login?: string
  permissions: {
    can_view_analytics: boolean
    can_manage_users: boolean
    is_teacher: boolean
    is_student: boolean
    is_admin: boolean
  }
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  first_name: string
  last_name: string
  role?: 'student' | 'teacher'
  group_id?: number
  student_id?: string
}

export interface AuthResponse {
  message: string
  user: User
  token: string
}

export interface APIError {
  error: string
}

// Создаем axios instance для авторизации
const authAPI = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Интерсептор для добавления токена к запросам
authAPI.interceptors.request.use(
  (config) => {
    const token = AuthService.getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

// Интерсептор для обработки ошибок
authAPI.interceptors.response.use(
  (response: AxiosResponse) => {
    console.log(`✅ Auth API Response: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error('❌ Auth API Error:', error.response?.status, error.message)

    // Если получили 401, очищаем токен
    if (error.response?.status === 401) {
      AuthService.logout()
    }

    const apiError: APIError = {
      error: error.response?.data?.error || error.message || 'Произошла ошибка',
    }

    return Promise.reject(apiError)
  },
)

// Сервис авторизации
export class AuthService {
  private static readonly TOKEN_KEY = 'ai_detection_token'
  private static readonly USER_KEY = 'ai_detection_user'

  // Методы для работы с токеном
  static getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY)
  }

  static setToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token)
  }

  static removeToken(): void {
    localStorage.removeItem(this.TOKEN_KEY)
  }

  // Методы для работы с данными пользователя
  static getUser(): User | null {
    const userData = localStorage.getItem(this.USER_KEY)
    if (userData) {
      try {
        return JSON.parse(userData)
      } catch (e) {
        console.error('Error parsing user data:', e)
        this.removeUser()
      }
    }
    return null
  }

  static setUser(user: User): void {
    localStorage.setItem(this.USER_KEY, JSON.stringify(user))
  }

  static removeUser(): void {
    localStorage.removeItem(this.USER_KEY)
  }

  // Проверка авторизации
  static isAuthenticated(): boolean {
    const token = this.getToken()
    const user = this.getUser()
    return !!(token && user)
  }

  // Проверка роли
  static hasRole(role: string): boolean {
    const user = this.getUser()
    return user?.role === role
  }

  static hasAnyRole(roles: string[]): boolean {
    const user = this.getUser()
    return user ? roles.includes(user.role) : false
  }

  // Проверка разрешений
  static canViewAnalytics(): boolean {
    const user = this.getUser()
    return user?.permissions?.can_view_analytics || false
  }

  static canManageUsers(): boolean {
    const user = this.getUser()
    return user?.permissions?.can_manage_users || false
  }

  // Вход в систему
  static async login(credentials: LoginRequest): Promise<AuthResponse> {
    try {
      const response = await authAPI.post<AuthResponse>('/api/auth/login', credentials)
      const { user, token } = response.data

      // Сохраняем данные
      this.setToken(token)
      this.setUser(user)

      console.log('✅ Успешный вход:', user.email)
      return response.data
    } catch (error) {
      console.error('❌ Ошибка входа:', error)
      throw error
    }
  }

  // Регистрация
  static async register(userData: RegisterRequest): Promise<AuthResponse> {
    try {
      const response = await authAPI.post<AuthResponse>('/api/auth/register', userData)
      const { user, token } = response.data

      // Сохраняем данные
      this.setToken(token)
      this.setUser(user)

      console.log('✅ Успешная регистрация:', user.email)
      return response.data
    } catch (error) {
      console.error('❌ Ошибка регистрации:', error)
      throw error
    }
  }

  // Получение информации о текущем пользователе
  static async getCurrentUser(): Promise<User> {
    try {
      const response = await authAPI.get<{ user: User }>('/api/auth/me')
      const user = response.data.user

      // Обновляем локальные данные
      this.setUser(user)

      return user
    } catch (error) {
      console.error('❌ Ошибка получения пользователя:', error)
      throw error
    }
  }

  // Обновление токена
  static async refreshToken(): Promise<string> {
    try {
      const response = await authAPI.post<{ token: string; user: User }>('/api/auth/refresh')
      const { token, user } = response.data

      this.setToken(token)
      this.setUser(user)

      return token
    } catch (_error) {
      this.logout()
      throw _error
    }
  }

  // Выход из системы
  static async logout(): Promise<void> {
    try {
      // Отправляем запрос на сервер (опционально)
      if (this.getToken()) {
        await authAPI.post('/api/auth/logout')
      }
    } catch (error) {
    } finally {
      // Очищаем локальные данные в любом случае
      this.removeToken()
      this.removeUser()
      console.log('✅ Выход выполнен')
    }
  }

  // Проверка валидности токена
  static async validateToken(): Promise<boolean> {
    try {
      await this.getCurrentUser()
      return true
    } catch {
      return false
    }
  }
}

// Экспортируем готовый сервис
export const authService = AuthService

// Дополнительные утилиты
export const getAuthHeaders = (): Record<string, string> => {
  const token = AuthService.getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export const getUserDisplayName = (user?: User | null): string => {
  if (!user) return 'Пользователь'
  return user.full_name || `${user.first_name} ${user.last_name}` || user.email
}

export const getRoleDisplayName = (role: string): string => {
  const roleNames = {
    student: 'Студент',
    teacher: 'Преподаватель',
    admin: 'Администратор',
    developer: 'Разработчик',
  }
  return roleNames[role as keyof typeof roleNames] || role
}

// Стартовый маршрут под роль: студент — самопроверка работы,
// преподаватель/админ — пакетная проверка студенческих работ.
export const defaultRouteForRole = (role?: string | null): string => {
  switch (role) {
    case 'teacher':
    case 'admin':
      return '/batch'
    default:
      return '/'
  }
}
