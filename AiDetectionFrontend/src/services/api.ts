import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'
import type {
  AnalyzeResponse,
  AnalyzeBatchResponse,
  HistoryResponse,
  DetectionDetail,
  StatsResponse,
  APIError,
  AllowedFileType,
  HistoryFilters,
} from '../types/api'

// Конфигурация API
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'

// Отладочная информация
console.log('🔧 API Configuration:', {
  API_BASE_URL,
  environment: import.meta.env.MODE,
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
})

// Разрешенные типы файлов
const ALLOWED_FILE_TYPES: AllowedFileType[] = ['pdf', 'docx', 'doc', 'txt']

// Создаем axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Интерсептор для добавления токена авторизации
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('ai_detection_token')
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
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error) => {
    const apiError: APIError = {
      error: error.response?.data?.error || error.message || 'Произошла ошибка',
    }

    return Promise.reject(apiError)
  },
)

// Утилитарные функции
export const isValidFileType = (file: File): boolean => {
  const extension = file.name.split('.').pop()?.toLowerCase()
  return extension ? ALLOWED_FILE_TYPES.includes(extension as AllowedFileType) : false
}

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Функции для работы с вероятностью ИИ
export const getAILikelihoodLabel = (likelihood?: number): string => {
  if (!likelihood) return 'Неизвестно'
  if (likelihood >= 0.8) return 'Очень высокая'
  if (likelihood >= 0.5) return 'Высокая'
  if (likelihood >= 0.2) return 'Средняя'
  return 'Низкая'
}

export const getAILikelihoodColor = (likelihood?: number): string => {
  if (!likelihood) return 'gray'
  if (likelihood >= 0.8) return 'red'
  if (likelihood >= 0.5) return 'orange'
  if (likelihood >= 0.2) return 'yellow'
  return 'green'
}

// API класс
export class AIDetectionAPI {
  // Анализ текста
  async analyzeText(text: string, detailedAnalysis: boolean = false): Promise<AnalyzeResponse> {
    const response = await api.post<AnalyzeResponse>('/analyze-text', {
      text,
      detailed_analysis: detailedAnalysis,
    })
    return response.data
  }

  // Загрузка и анализ файла
  async uploadFile(file: File, detailedAnalysis: boolean = false): Promise<AnalyzeResponse> {
    if (!isValidFileType(file)) {
      throw new Error(`Неподдерживаемый тип файла. Разрешены: ${ALLOWED_FILE_TYPES.join(', ')}`)
    }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('detailed_analysis', detailedAnalysis.toString())

    const response = await api.post<AnalyzeResponse>('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  // Пакетный анализ текстов
  async analyzeBatch(texts: string[]): Promise<AnalyzeBatchResponse> {
    const response = await api.post<AnalyzeBatchResponse>('/analyze-batch', { texts })
    return response.data
  }

  // Получение истории
  async getHistory(
    page: number = 1,
    perPage: number = 10,
    filters?: HistoryFilters,
  ): Promise<HistoryResponse> {
    const response = await api.get<HistoryResponse>('/history', {
      params: { page, per_page: perPage, ...filters },
    })
    return response.data
  }

  // Получение детальной информации о проверке
  async getDetection(id: number): Promise<DetectionDetail> {
    const response = await api.get<DetectionDetail>(`/history/${id}`)
    return response.data
  }

  // Получение статистики
  async getStats(): Promise<StatsResponse> {
    const response = await api.get<StatsResponse>('/stats')
    return response.data
  }

  // Получение отчета о плагиате
  async getPlagiarismReport(detectionId: number): Promise<any> {
    const response = await api.get(`/plagiarism/${detectionId}`)
    return response.data
  }

  // Загрузка PDF отчета о плагиате
  async downloadPlagiarismPDF(detectionId: number): Promise<Blob> {
    const response = await api.get(`/plagiarism/${detectionId}/pdf`, {
      responseType: 'blob',
    })
    return response.data as Blob
  }

  // Статистика корпуса
  async getCorpusStats(): Promise<any> {
    const response = await api.get('/plagiarism/corpus-stats')
    return response.data
  }

  // Повторная проверка на плагиат
  async recheckPlagiarism(detectionId: number): Promise<any> {
    const response = await api.post(`/plagiarism/recheck/${detectionId}`)
    return response.data
  }
}

// Экспортируем единственный экземпляр API
export const aiDetectionAPI = new AIDetectionAPI()

// Дополнительные утилиты
export const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export const truncateText = (text: string, maxLength: number = 100): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}
