<template>
  <div class="space-y-6">
    <!-- Список анализов -->
    <div v-if="hasDetections" class="space-y-4">
      <div
        v-for="detection in detections"
        :key="detection.id"
        class="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer"
        @click="viewDetails(detection.id)"
      >
        <div class="flex justify-between items-start mb-4">
          <div class="flex-1">
            <h3 class="text-lg font-semibold text-gray-900 mb-2">
              {{
                detection.filename === 'direct_text_input'
                  ? 'Ручной ввод текста'
                  : detection.filename
              }}
            </h3>
            <div class="flex flex-wrap gap-2 mb-3">
              <Tag
                :value="detection.file_type?.toUpperCase() || 'TEXT'"
                severity="info"
                class="text-xs"
              />
              <Tag :value="`${detection.text_length} слов`" severity="secondary" class="text-xs" />
              <Tag :value="formatDate(detection.created_at)" severity="secondary" class="text-xs" />
            </div>
          </div>
          <div class="flex items-center gap-4">
            <div class="text-right">
              <div class="text-sm text-gray-600">Вероятность ИИ</div>
              <Tag
                :value="formatPercentage(detection.ai_likelihood || 0)"
                :severity="getAILikelihoodSeverity(detection.ai_likelihood || 0)"
                class="font-semibold"
              />
            </div>

            <!-- Дополнительные действия -->
            <div class="flex gap-2">
              <!-- Кнопка PDF отчета -->
              <Button
                :icon="isDownloadingPDF[detection.id] ? 'pi pi-spin pi-spinner' : 'pi pi-file-pdf'"
                severity="danger"
                outlined
                :disabled="isDownloadingPDF[detection.id]"
                @click.stop="downloadPDFReport(detection.id)"
                class="!p-2"
                v-tooltip="'Скачать PDF отчет'"
              />

              <!-- Кнопка антиплагиата (если есть данные) -->
              <Button
                icon="pi pi-copy"
                severity="warning"
                outlined
                @click.stop="viewPlagiarismReport(detection.id)"
                class="!p-2"
                v-tooltip="'Детальный отчет о плагиате'"
              />

              <!-- Кнопка деталей -->
              <Button
                icon="pi pi-arrow-right"
                severity="secondary"
                outlined
                @click.stop="viewDetails(detection.id)"
                class="!p-2"
                v-tooltip="'Подробности анализа'"
              />
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span class="text-gray-600">Предсказание:</span>
            <div class="font-medium mt-1">{{ detection.prediction || 'N/A' }}</div>
          </div>
          <div>
            <span class="text-gray-600">API:</span>
            <div class="font-medium mt-1">
              {{ detection.api_endpoint?.includes('sliding') ? 'Детальный' : 'Стандартный' }}
            </div>
          </div>
          <div v-if="detection.plagiarism_originality !== undefined">
            <span class="text-gray-600">Оригинальность:</span>
            <div class="font-medium mt-1">{{ Math.round(detection.plagiarism_originality) }}%</div>
          </div>
          <div v-if="detection.plagiarism_level">
            <span class="text-gray-600">Плагиат:</span>
            <div class="font-medium mt-1">
              <Tag
                :value="getPlagiarismLevelLabel(detection.plagiarism_level)"
                :severity="getPlagiarismSeverity(detection.plagiarism_level)"
                class="text-xs"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Пустое состояние -->
    <div v-else-if="!isLoading" class="text-center py-12">
      <i class="pi pi-file-o text-6xl text-gray-300 mb-4"></i>
      <h3 class="text-xl font-semibold text-gray-600 mb-2">Анализы не найдены</h3>
      <p class="text-gray-500 mb-6">
        Попробуйте изменить параметры фильтрации или загрузите новый файл для анализа
      </p>
      <Button label="Загрузить файл" @click="router.push('/')" icon="pi pi-upload" />
    </div>

    <!-- Состояние загрузки -->
    <div v-else class="text-center py-12">
      <ProgressSpinner />
      <p class="text-gray-500 mt-4">Загрузка истории анализов...</p>
    </div>

    <!-- Пагинация -->
    <div v-if="hasDetections && pagination" class="flex justify-between items-center pt-6">
      <div class="text-sm text-gray-600">
        Показано {{ detections.length }} из {{ pagination.total }} результатов
      </div>
      <div class="flex gap-2">
        <Button
          label="Предыдущая"
          icon="pi pi-chevron-left"
          :disabled="isFirstPage"
          @click="loadPreviousPage"
          severity="secondary"
          outlined
        />
        <Button
          label="Следующая"
          icon="pi pi-chevron-right"
          :disabled="isLastPage"
          @click="loadNextPage"
          severity="secondary"
          outlined
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import { useAIDetectionStore } from '../stores/aiDetection'
import { formatDate } from '../services/api'
import { ref } from 'vue'

// Пропсы
interface Props {
  autoOpenId?: number | null
}

const props = withDefaults(defineProps<Props>(), {
  autoOpenId: null,
})

const router = useRouter()
const store = useAIDetectionStore()
const { isLoading, detections, hasDetections, pagination, isFirstPage, isLastPage } =
  storeToRefs(store)

// Состояние загрузки PDF для каждой детекции
const isDownloadingPDF = ref<Record<number, boolean>>({})

// Методы
const viewDetails = (id: number) => {
  router.push(`/analysis/${id}`)
}

const viewPlagiarismReport = (id: number) => {
  router.push(`/plagiarism/${id}`)
}

const downloadPDFReport = async (id: number) => {
  isDownloadingPDF.value[id] = true

  try {
    const token = localStorage.getItem('ai_detection_token')
    if (!token) {
      alert('Требуется авторизация')
      return
    }

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'
    const response = await fetch(`${API_BASE_URL}/api/reports/detection/${id}/pdf`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (response.ok) {
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `detection-report-${id}.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } else {
      const errorData = await response.json()
      alert(errorData.error || 'Ошибка генерации PDF')
    }
  } catch (error) {
    console.error('PDF download error:', error)
    alert('Ошибка скачивания PDF отчета')
  } finally {
    isDownloadingPDF.value[id] = false
  }
}

const loadPreviousPage = () => {
  if (!isFirstPage.value) {
    store.loadHistory({ page: pagination.value!.currentPage - 1 })
  }
}

const loadNextPage = () => {
  if (!isLastPage.value) {
    store.loadHistory({ page: pagination.value!.currentPage + 1 })
  }
}

// Утилиты
const formatPercentage = (value: number): string => {
  return `${Math.round(value * 100)}%`
}

const getAILikelihoodSeverity = (likelihood: number): string => {
  if (likelihood >= 0.8) return 'danger'
  if (likelihood >= 0.5) return 'warning'
  if (likelihood >= 0.2) return 'info'
  return 'success'
}

const getPlagiarismLevelLabel = (level: string): string => {
  const labels: Record<string, string> = {
    original: 'Оригинал',
    low: 'Низкий',
    moderate: 'Средний',
    high: 'Высокий',
    very_high: 'Очень высокий',
  }
  return labels[level] || level
}

const getPlagiarismSeverity = (level: string): string => {
  const severities: Record<string, string> = {
    original: 'success',
    low: 'info',
    moderate: 'warning',
    high: 'danger',
    very_high: 'danger',
  }
  return severities[level] || 'secondary'
}
</script>
