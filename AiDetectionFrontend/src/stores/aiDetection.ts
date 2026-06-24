import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { aiDetectionAPI } from '../services/api'
import type {
  Detection,
  DetectionDetail,
  AnalyzeResponse,
  AnalyzeBatchResponse,
  StatsResponse,
  APIError,
  HistoryFilters,
  AnalysisProvider,
} from '../types/api'

export const useAIDetectionStore = defineStore('aiDetection', () => {
  // Состояние
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const detections = ref<Detection[]>([])
  const currentDetection = ref<DetectionDetail | null>(null)
  const stats = ref<StatsResponse | null>(null)
  const filters = ref<HistoryFilters>({})
  const pagination = ref({
    currentPage: 1,
    totalPages: 1,
    total: 0,
    perPage: 10,
  })

  // Computed
  const hasDetections = computed(() => detections.value.length > 0)
  const isFirstPage = computed(() => pagination.value.currentPage === 1)
  const isLastPage = computed(() => pagination.value.currentPage === pagination.value.totalPages)

  // Действия
  const clearError = () => {
    error.value = null
  }

  const setLoading = (loading: boolean) => {
    isLoading.value = loading
    if (loading) {
      error.value = null
    }
  }

  const handleError = (err: unknown) => {
    console.error('Store error:', err)
    if (typeof err === 'object' && err !== null && 'error' in err) {
      error.value = (err as APIError).error
    } else if (err instanceof Error) {
      error.value = err.message
    } else {
      error.value = 'Произошла неизвестная ошибка'
    }
  }

  // Анализ текста
  const analyzeText = async (
    text: string,
    detailedAnalysis: boolean = false,
    analysisProvider: AnalysisProvider = 'pangram',
  ): Promise<AnalyzeResponse | null> => {
    try {
      setLoading(true)
      const result = await aiDetectionAPI.analyzeText(text, detailedAnalysis, analysisProvider)
      return result
    } catch (err) {
      handleError(err)
      return null
    } finally {
      setLoading(false)
    }
  }

  // Загрузка файла
  const uploadFile = async (
    file: File,
    detailedAnalysis: boolean = false,
    analysisProvider: AnalysisProvider = 'pangram',
  ): Promise<AnalyzeResponse | null> => {
    try {
      setLoading(true)
      const result = await aiDetectionAPI.uploadFile(file, detailedAnalysis, analysisProvider)
      return result
    } catch (err) {
      handleError(err)
      return null
    } finally {
      setLoading(false)
    }
  }

  // Пакетный анализ
  const analyzeBatch = async (texts: string[]): Promise<AnalyzeBatchResponse | null> => {
    try {
      setLoading(true)
      const result = await aiDetectionAPI.analyzeBatch(texts)
      return result
    } catch (err) {
      handleError(err)
      return null
    } finally {
      setLoading(false)
    }
  }

  // Загрузка истории
  const loadHistory = async (options: { page?: number } | number = {}) => {
    try {
      setLoading(true)
      const page = typeof options === 'number' ? options : (options.page || 1)
      const result = await aiDetectionAPI.getHistory(page, pagination.value.perPage, filters.value)

      detections.value = result.detections
      pagination.value = {
        currentPage: result.current_page,
        totalPages: result.pages,
        total: result.total,
        perPage: result.per_page ?? pagination.value.perPage,
      }
    } catch (err) {
      handleError(err)
    } finally {
      setLoading(false)
    }
  }

  // Загрузка детальной информации
  const loadDetection = async (id: number): Promise<DetectionDetail | null> => {
    try {
      setLoading(true)
      const result = await aiDetectionAPI.getDetection(id)
      currentDetection.value = result
      return result
    } catch (err) {
      handleError(err)
      return null
    } finally {
      setLoading(false)
    }
  }

  // Загрузка детальной информации (алиас для совместимости)
  const loadDetectionDetails = async (id: number): Promise<DetectionDetail | null> => {
    return await loadDetection(id)
  }

  // Загрузка статистики
  const loadStats = async () => {
    try {
      const result = await aiDetectionAPI.getStats()
      stats.value = result
    } catch (err) {
      console.error('Ошибка загрузки статистики:', err)
      // Не показываем ошибку статистики пользователю, это не критично
    }
  }

  // Навигация по страницам
  const nextPage = async () => {
    if (!isLastPage.value) {
      await loadHistory({ page: pagination.value.currentPage + 1 })
    }
  }

  const prevPage = async () => {
    if (!isFirstPage.value) {
      await loadHistory({ page: pagination.value.currentPage - 1 })
    }
  }

  const goToPage = async (page: number) => {
    if (page >= 1 && page <= pagination.value.totalPages) {
      await loadHistory({ page })
    }
  }

  // Очистка данных
  const clearDetections = () => {
    detections.value = []
    currentDetection.value = null
    pagination.value = {
      currentPage: 1,
      totalPages: 1,
      total: 0,
      perPage: 10,
    }
  }

  const clearCurrentDetection = () => {
    currentDetection.value = null
  }

  // Методы для работы с фильтрами
  const setFilters = (newFilters: HistoryFilters) => {
    filters.value = { ...newFilters }
  }

  const clearFilters = () => {
    filters.value = {}
  }

  const applyFilters = async (newFilters: HistoryFilters) => {
    filters.value = { ...newFilters }
    await loadHistory({ page: 1 }) // Сбрасываем на первую страницу при фильтрации
  }

  return {
    // State
    isLoading,
    error,
    detections,
    currentDetection,
    stats,
    pagination,
    filters,

    // Computed
    hasDetections,
    isFirstPage,
    isLastPage,

    // Actions
    clearError,
    analyzeText,
    uploadFile,
    analyzeBatch,
    loadHistory,
    loadDetection,
    loadDetectionDetails,
    loadStats,
    nextPage,
    prevPage,
    goToPage,
    clearDetections,
    clearCurrentDetection,
    setFilters,
    clearFilters,
    applyFilters,
  }
})
