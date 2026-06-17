<template>
  <div class="bg-white rounded-lg shadow-lg p-4 sm:p-8">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-4">
      <h2 class="text-xl sm:text-2xl font-bold text-black">Анализ текста на наличие ИИ</h2>

      <!-- Тогл детального анализа -->
      <div class="flex items-center gap-2">
        <ToggleSwitch
          v-model="detailedAnalysis"
          :disabled="isLoading"
          class="custom-toggle"
          v-tooltip.left="{
            value: detailedAnalysis
              ? 'Использует алгоритм sliding window с цветной сегментацией текста. Более точный, но дороже.'
              : 'Использует стандартный анализ без сегментации',
            class: 'max-w-xs',
          }"
        />
        <span
          :class="[
            'text-xs sm:text-sm font-medium transition-colors',
            detailedAnalysis ? 'text-green-600' : 'text-gray-500',
          ]"
        >
          Детальный анализ
        </span>
      </div>
    </div>

    <!-- Переключатель режимов -->
    <div class="flex mb-6 bg-gray-100 rounded-lg p-1">
      <Button
        :class="[
          'flex-1 mx-1 py-2 px-2 sm:px-4 rounded-lg font-medium text-xs sm:text-sm',
          mode === 'text'
            ? 'bg-blue-600 text-white'
            : 'bg-transparent text-black hover:bg-gray-200',
        ]"
        @click="mode = 'text'"
        icon="pi pi-file-edit"
        label="Ввод текста"
      />
      <Button
        :class="[
          'flex-1 mx-1 py-2 px-2 sm:px-4 rounded-lg font-medium text-xs sm:text-sm',
          mode === 'file'
            ? 'bg-blue-600 text-white'
            : 'bg-transparent text-black hover:bg-gray-200',
        ]"
        @click="mode = 'file'"
        icon="pi pi-upload"
        label="Загрузка файла"
      />
    </div>

    <!-- Ввод текста -->
    <div v-if="mode === 'text'" class="space-y-4">
      <div>
        <label class="block text-lg font-medium text-black mb-2"> Введите текст для анализа </label>
        <Textarea
          v-model="textInput"
          rows="8"
          class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-black"
          placeholder="Вставьте сюда текст, который нужно проверить на наличие ИИ..."
          :disabled="isLoading"
        />
        <div class="text-sm text-gray-500 mt-1">Символов: {{ textInput.length }}</div>
      </div>

      <Button
        @click="handleTextAnalysis"
        :disabled="!textInput.trim() || isLoading"
        :loading="isLoading"
        icon="pi pi-search"
        label="Анализировать текст"
        class="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
      />
    </div>

    <!-- Загрузка файла -->
    <div v-if="mode === 'file'" class="space-y-4">
      <div>
        <label class="block text-lg font-medium text-black mb-2"> Выберите файл для анализа </label>
        <div class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
          <FileUpload
            mode="basic"
            :auto="false"
            :multiple="false"
            accept=".pdf,.docx,.doc,.txt"
            :maxFileSize="16777216"
            @select="onFileSelect"
            @clear="clearFile"
            :disabled="isLoading"
            chooseLabel="Выбрать файл"
            class="w-full"
          />
        </div>
        <div class="text-sm text-gray-500 mt-2">
          Поддерживаемые форматы: PDF, DOCX, DOC, TXT (максимум 16 МБ)
        </div>
      </div>

      <!-- Информация о файле -->
      <div v-if="selectedFile" class="bg-blue-50 p-4 rounded-lg">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div class="flex items-center">
            <i class="pi pi-file text-blue-600 text-xl mr-3"></i>
            <div>
              <div class="font-medium text-black break-all">{{ selectedFile.name }}</div>
              <div class="text-sm text-gray-500">{{ formatFileSize(selectedFile.size) }}</div>
            </div>
          </div>

          <!-- Чипсы с информацией -->
          <div v-if="fileInfo" class="flex flex-wrap gap-2">
            <div
              class="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-xs sm:text-sm font-medium"
            >
              {{ fileInfo.word_count }} слов
            </div>
            <div
              class="bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-xs sm:text-sm font-medium"
            >
              {{ fileInfo.char_count }} символов
            </div>
          </div>
        </div>

        <!-- Прогресс загрузки -->
        <div v-if="isFileUploading" class="mt-3">
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div
              class="bg-blue-600 h-2 rounded-full transition-all duration-300"
              :style="uploadProgressStyle"
            ></div>
          </div>
          <div class="text-sm text-gray-600 mt-1">Получение информации о файле...</div>
        </div>
      </div>

      <Button
        @click="handleFileAnalysis"
        :disabled="!selectedFile || isLoading"
        :loading="isLoading"
        icon="pi pi-search"
        label="Анализировать файл"
        class="w-full py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium"
      />
    </div>

    <!-- Результат анализа -->
    <div v-if="analysisResult" class="mt-6 p-4 bg-gray-100 rounded-lg border">
      <h3 class="text-lg font-semibold mb-3 text-black">Результат анализа</h3>

      <!-- Анализируемый текст с сегментацией -->
      <div v-if="hasSegmentedView" class="mb-6">
        <h4 class="text-md font-medium text-black mb-3">Анализируемый текст:</h4>
        <div class="bg-white p-4 rounded border max-h-96 overflow-y-auto">
          <div class="text-sm leading-relaxed text-black whitespace-pre-wrap">
            <span
              v-for="(segment, index) in getTextSegments()"
              :key="index"
              :class="getSegmentClass(segment.ai_likelihood)"
              :title="`Сегмент ${index + 1}: ${formatPercentage(segment.ai_likelihood)} вероятность ИИ`"
              class="cursor-help transition-all duration-200 hover:shadow-sm"
              >{{ segment.text }}</span
            >
          </div>

          <!-- Легенда -->
          <div class="mt-4 pt-4 border-t border-gray-200">
            <div class="text-xs text-gray-600 mb-2">Цветовая схема вероятности ИИ:</div>
            <div class="flex flex-wrap gap-2 text-xs">
              <div class="flex items-center gap-1">
                <div class="w-3 h-3 bg-red-200 border border-red-400 rounded"></div>
                <span>80-100%</span>
              </div>
              <div class="flex items-center gap-1">
                <div class="w-3 h-3 bg-orange-200 border border-orange-400 rounded"></div>
                <span>50-80%</span>
              </div>
              <div class="flex items-center gap-1">
                <div class="w-3 h-3 bg-yellow-200 border border-yellow-400 rounded"></div>
                <span>20-50%</span>
              </div>
              <div class="flex items-center gap-1">
                <div class="w-3 h-3 bg-green-200 border border-green-400 rounded"></div>
                <span>0-20%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="space-y-3">
        <div class="bg-white p-3 rounded border">
          <div class="text-sm text-gray-600">ID анализа</div>
          <div class="font-bold text-lg text-black">{{ analysisResult.detection_id }}</div>
        </div>
        <div class="bg-white p-3 rounded border">
          <div class="text-sm text-gray-600">Длина текста</div>
          <div class="font-bold text-lg text-black">{{ analysisResult.text_length }} слов</div>
        </div>
        <div
          v-if="analysisResult.pangram_response.ai_likelihood"
          class="bg-white p-3 rounded border"
        >
          <div class="text-sm text-gray-600 mb-2 flex items-center gap-1">
            <i class="pi pi-robot text-blue-500"></i>
            Вероятность ИИ
          </div>
          <SmartTag
            :value="formatPercentage(analysisResult.pangram_response.ai_likelihood)"
            :severity="getAILikelihoodSeverity(analysisResult.pangram_response.ai_likelihood)"
            type="ai-likelihood"
            :ai-likelihood="analysisResult.pangram_response.ai_likelihood"
            class="font-bold"
          />
        </div>

        <!-- Информация о плагиате -->
        <div v-if="analysisResult.plagiarism_report" class="bg-white p-3 rounded border">
          <div class="text-sm text-gray-600 mb-2 flex items-center gap-1">
            <i class="pi pi-book text-purple-500"></i>
            Анализ плагиата
          </div>
          <div class="flex items-center justify-between">
            <div>
              <SmartTag
                :value="`${Math.round(analysisResult.plagiarism_report.originality_percentage)}% оригинальности`"
                :severity="
                  getPlagiarismSeverity(analysisResult.plagiarism_report.originality_percentage)
                "
                type="plagiarism"
                :originality="analysisResult.plagiarism_report.originality_percentage"
                class="font-bold"
              />
              <div class="text-xs text-gray-500 mt-1">
                {{ getPlagiarismLevelLabel(analysisResult.plagiarism_report.plagiarism_level) }}
              </div>
            </div>
            <div
              v-if="analysisResult.plagiarism_report.similar_documents.length > 0"
              class="text-xs text-gray-500 flex items-center gap-1"
              v-tooltip.top="
                `Найдено ${analysisResult.plagiarism_report.similar_documents.length} документов с похожим содержимым в базе данных`
              "
            >
              <i class="pi pi-file-o"></i>
              {{ analysisResult.plagiarism_report.similar_documents.length }} похожих документов
            </div>
          </div>
        </div>
      </div>

      <div class="mt-4 space-y-2">
        <div class="flex gap-2">
          <Button
            @click="router.push(`/analysis/${analysisResult.detection_id}`)"
            icon="pi pi-eye"
            label="Детальный анализ"
            class="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
          />
          <Button
            v-if="analysisResult.plagiarism_report"
            @click="router.push(`/plagiarism/${analysisResult.detection_id}`)"
            icon="pi pi-book"
            label="Анализ плагиата"
            class="flex-1 bg-purple-600 hover:bg-purple-700 text-white"
          />
        </div>
        <Button
          @click="router.push('/history')"
          icon="pi pi-history"
          label="Вся история"
          outlined
          class="w-full bg-white hover:bg-gray-100"
        />
      </div>
    </div>

    <!-- Ошибка -->
    <Message v-if="error" severity="error" :closable="false" class="mt-4">
      {{ error }}
    </Message>

    <!-- AI Detection Banner -->
    <AIDetectionBanner
      v-if="aiSegmentsCount > 0"
      :show="showAIAlert"
      :ai-segments="aiSegmentsCount"
      :total-segments="totalSegmentsCount"
      :confidence="Math.round(currentAnalysisConfidence * 100)"
      @close="showAIAlert = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import FileUpload from 'primevue/fileupload'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import ToggleSwitch from 'primevue/toggleswitch'
import type { FileUploadSelectEvent } from 'primevue/fileupload'
import { useAIDetectionStore } from '../stores/aiDetection'
import { formatFileSize, getAILikelihoodColor } from '../services/api'
import type { AnalyzeResponse, WindowData } from '../types/api'
import AIDetectionBanner from './AIDetectionBanner.vue'
import SmartTag from './common/SmartTag.vue'

const store = useAIDetectionStore()
const { isLoading, error } = storeToRefs(store)
const router = useRouter()

// Режим работы
const mode = ref<'text' | 'file'>('text')

// Состояние формы
const textInput = ref('')
const selectedFile = ref<File | null>(null)
const analysisResult = ref<AnalyzeResponse | null>(null)
const showAIAlert = ref(false)
const detailedAnalysis = ref(false)

// Новые состояния для файлов
const extractedText = ref('')
const fileWordCount = ref(0)
const fileInfo = ref<{ word_count: number; char_count: number } | null>(null)
const isFileUploading = ref(false)
const uploadProgress = ref(0)
const uploadProgressStyle = computed(() => ({ width: `${uploadProgress.value}%` }))

// AI Alert computed values
const aiSegmentsCount = computed(() => {
  if (!analysisResult.value?.pangram_response) return 0

  // Для детального анализа (с windows)
  if (analysisResult.value.pangram_response.windows) {
    const windows = analysisResult.value.pangram_response.windows as WindowData[]
    return windows.filter((window) => window.ai_likelihood >= 0.5).length
  }

  // Для стандартного анализа (без windows)
  const aiLikelihood = analysisResult.value.pangram_response.ai_likelihood || 0
  return aiLikelihood >= 0.5 ? 1 : 0
})

const totalSegmentsCount = computed(() => {
  if (!analysisResult.value?.pangram_response) return 0

  // Для детального анализа (с windows)
  if (analysisResult.value.pangram_response.windows) {
    return analysisResult.value.pangram_response.windows.length
  }

  // Для стандартного анализа (без windows) - считаем весь текст как 1 сегмент
  return 1
})

const currentAnalysisConfidence = computed(() => {
  return analysisResult.value?.pangram_response?.ai_likelihood || 0
})

// Методы
const onFileSelect = async (event: FileUploadSelectEvent) => {
  selectedFile.value = event.files[0]

  if (selectedFile.value) {
    await getFileInfo()
  }
}

const clearFile = () => {
  selectedFile.value = null
  extractedText.value = ''
  fileWordCount.value = 0
  fileInfo.value = null
  isFileUploading.value = false
  uploadProgress.value = 0
}

const getFileInfo = async () => {
  if (!selectedFile.value) return

  isFileUploading.value = true
  uploadProgress.value = 0

  try {
    // Симуляция прогресса
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10
      }
    }, 200)

    // Создаем FormData для получения информации о файле
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    // Отправляем запрос на получение информации о файле
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/file-info`, {
      method: 'POST',
      body: formData,
    })

    clearInterval(progressInterval)
    uploadProgress.value = 100

    if (response.ok) {
      const data = await response.json()
      fileInfo.value = {
        word_count: data.word_count || 0,
        char_count: data.char_count || 0,
      }
    } else {
      const errorData = await response.json()
      error.value = errorData.error || 'Ошибка при получении информации о файле'
    }
  } catch (err) {
    console.error('Ошибка при получении информации о файле:', err)
    error.value = 'Ошибка при получении информации о файле'
  } finally {
    isFileUploading.value = false
  }
}

const handleTextAnalysis = async () => {
  if (!textInput.value.trim()) return

  analysisResult.value = null
  const result = await store.analyzeText(textInput.value.trim(), detailedAnalysis.value)
  if (result) {
    analysisResult.value = result

    // Показываем AI Alert если обнаружен ИИ
    if (result.pangram_response.ai_likelihood && result.pangram_response.ai_likelihood >= 0.5) {
      setTimeout(() => {
        showAIAlert.value = true
      }, 1000)
    }
  }
}

const handleFileAnalysis = async () => {
  if (!selectedFile.value) return

  analysisResult.value = null
  // Отправляем сам файл на анализ
  const result = await store.uploadFile(selectedFile.value, detailedAnalysis.value)
  if (result) {
    analysisResult.value = result

    // Показываем AI Alert если обнаружен ИИ
    if (result.pangram_response.ai_likelihood && result.pangram_response.ai_likelihood >= 0.5) {
      setTimeout(() => {
        showAIAlert.value = true
      }, 1000)
    }
  }
}

const formatPercentage = (value: number): string => {
  return `${Math.round(value * 100)}%`
}

const getAILikelihoodSeverity = (
  likelihood: number,
): 'success' | 'info' | 'warning' | 'danger' | 'secondary' => {
  const color = getAILikelihoodColor(likelihood)
  switch (color) {
    case 'red':
      return 'danger'
    case 'orange':
      return 'warning'
    case 'yellow':
      return 'info'
    case 'green':
      return 'success'
    default:
      return 'secondary'
  }
}

const getPlagiarismSeverity = (
  originality: number,
): 'success' | 'info' | 'warning' | 'danger' | 'secondary' => {
  if (originality >= 85) return 'success'
  if (originality >= 70) return 'warning'
  if (originality >= 50) return 'warning'
  return 'danger'
}

const getPlagiarismLevelLabel = (level: string) => {
  const labels = {
    original: 'Оригинальный',
    low: 'Низкий риск',
    moderate: 'Средний риск',
    high: 'Высокий риск',
    very_high: 'Очень высокий риск',
  }
  return labels[level as keyof typeof labels] || level
}

const getAILikelihoodDescription = (likelihood: number): string => {
  if (likelihood >= 0.8) return 'Текст скорее всего создан ИИ'
  if (likelihood >= 0.5) return 'Высокая вероятность использования ИИ'
  if (likelihood >= 0.2) return 'Возможно частичное использование ИИ'
  return 'Текст вероятно написан человеком'
}

const getPlagiarismDescription = (originality: number): string => {
  if (originality >= 85) return 'Отличная оригинальность, плагиат не обнаружен'
  if (originality >= 70) return 'Хорошая оригинальность, незначительные совпадения'
  if (originality >= 50) return 'Средняя оригинальность, есть подозрительные фрагменты'
  return 'Низкая оригинальность, обнаружен значительный плагиат'
}

const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

const hasSegmentedView = computed(() => {
  return (
    analysisResult.value?.pangram_response?.windows &&
    analysisResult.value.pangram_response.windows.length > 0
  )
})

const getTextSegments = () => {
  if (!analysisResult.value?.pangram_response?.windows) return []
  return analysisResult.value.pangram_response.windows as WindowData[]
}

const getSegmentClass = (likelihood: number) => {
  const baseClass = 'inline-block transition-all duration-200 hover:shadow-sm cursor-help'

  if (likelihood >= 0.8) {
    return `${baseClass} bg-red-200 text-red-900 border-l-4 border-red-600 px-1 py-0.5 mx-0.5`
  }
  if (likelihood >= 0.5) {
    return `${baseClass} bg-orange-200 text-orange-900 border-l-4 border-orange-600 px-1 py-0.5 mx-0.5`
  }
  if (likelihood >= 0.2) {
    return `${baseClass} bg-yellow-200 text-yellow-900 border-l-4 border-yellow-600 px-1 py-0.5 mx-0.5`
  }
  return `${baseClass} bg-green-200 text-green-900 border-l-4 border-green-600 px-1 py-0.5 mx-0.5`
}
</script>

<style scoped>
/* Стили для textarea */
:deep(.p-textarea) {
  background-color: white !important;
  color: black !important;
}

:deep(.p-textarea::placeholder) {
  color: #6b7280 !important;
  opacity: 1 !important;
}

:deep(.p-textarea:focus) {
  background-color: white !important;
  color: black !important;
}

:deep(.p-textarea:disabled) {
  background-color: #f9fafb !important;
  color: #6b7280 !important;
}

/* Кастомные стили для ToggleSwitch */
:deep(.custom-toggle) {
  --p-toggleswitch-width: 3.5rem;
  --p-toggleswitch-height: 1.75rem;
  --p-toggleswitch-border-radius: 1rem;
  --p-toggleswitch-handle-size: 1.5rem;
  --p-toggleswitch-handle-border-radius: 50%;

  /* Цвета для выключенного состояния */
  --p-toggleswitch-background: #e5e7eb;
  --p-toggleswitch-border-color: #d1d5db;
  --p-toggleswitch-handle-background: #ffffff;
  --p-toggleswitch-handle-color: #6b7280;

  /* Цвета для включенного состояния */
  --p-toggleswitch-checked-background: #34d399;
  --p-toggleswitch-checked-border-color: #34d399;
  --p-toggleswitch-checked-handle-background: #ffffff;
  --p-toggleswitch-checked-handle-color: #ffffff;

  /* Hover эффекты */
  --p-toggleswitch-hover-background: #d1d5db;
  --p-toggleswitch-checked-hover-background: #34d399;
  --p-toggleswitch-handle-hover-background: #f9fafb;
  --p-toggleswitch-checked-hover-border-color: #34d399;

  /* Переходы */
  --p-toggleswitch-transition-duration: 0.2s;
  --p-toggleswitch-slide-duration: 0.2s;

  /* Фокус */
  --p-toggleswitch-focus-ring-width: 2px;
  --p-toggleswitch-focus-ring-color: #34d399;
  --p-toggleswitch-focus-ring-offset: 2px;

  /* Тени */
  --p-toggleswitch-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  --p-toggleswitch-focus-ring-shadow: 0 0 0 var(--p-toggleswitch-focus-ring-width)
    var(--p-toggleswitch-focus-ring-color);
}
</style>
