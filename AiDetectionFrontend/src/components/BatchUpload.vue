<template>
  <div class="bg-white rounded-lg shadow-md p-6">
    <h3 class="text-xl font-bold text-gray-900 mb-6">Множественный анализ файлов</h3>

    <!-- Зона загрузки файлов -->
    <div
      @drop="handleDrop"
      @dragover.prevent
      @dragenter.prevent
      :class="[
        'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
        isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400',
      ]"
    >
      <div class="space-y-4">
        <div class="flex justify-center">
          <i class="pi pi-cloud-upload text-4xl text-gray-400"></i>
        </div>
        <div>
          <p class="text-lg font-medium text-gray-900">
            Перетащите файлы сюда или
            <label class="text-blue-600 hover:text-blue-500 cursor-pointer underline">
              выберите файлы
              <input
                ref="fileInput"
                type="file"
                multiple
                accept=".pdf,.docx,.doc,.txt"
                @change="handleFileSelect"
                class="hidden"
              />
            </label>
          </p>
          <p class="text-sm text-gray-500 mt-2">
            Поддерживаются файлы: PDF, DOCX, DOC, TXT (до 50 файлов)
          </p>
        </div>
      </div>
    </div>

    <!-- Настройки анализа -->
    <div v-if="files.length > 0" class="mt-6 p-4 bg-gray-100 rounded-lg">
      <h4 class="font-medium text-gray-900 mb-3">Настройки анализа</h4>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <span class="text-sm text-gray-600">Обычный анализ</span>
          <div
            @click="detailedAnalysis = !detailedAnalysis"
            :class="[
              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer',
              detailedAnalysis ? 'bg-blue-600' : 'bg-gray-200',
            ]"
          >
            <span
              :class="[
                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                detailedAnalysis ? 'translate-x-6' : 'translate-x-1',
              ]"
            />
          </div>
          <span class="text-sm text-gray-600">Детальный анализ</span>
        </div>
        <div class="text-sm text-gray-500">
          {{ files.length }} файл(ов) • ~{{ estimatedCost }} кредитов
        </div>
      </div>
    </div>

    <!-- Список файлов -->
    <div v-if="files.length > 0" class="mt-6">
      <div class="flex justify-between items-center mb-4">
        <h4 class="font-medium text-gray-900">Файлы для обработки ({{ files.length }}/50)</h4>
        <div class="flex gap-2">
          <Button
            label="Очистить все"
            severity="secondary"
            outlined
            size="small"
            @click="clearAll"
            :disabled="isProcessing"
          />
          <Button
            label="Начать анализ"
            :loading="isProcessing"
            @click="startBatchAnalysis"
            :disabled="files.length === 0"
          />
        </div>
      </div>

      <div class="space-y-3 max-h-96 overflow-y-auto">
        <div
          v-for="(fileItem, index) in files"
          :key="index"
          class="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
        >
          <div class="flex items-center gap-3 flex-1">
            <!-- Иконка файла -->
            <div class="flex-shrink-0">
              <i :class="getFileIcon(fileItem.file)" class="text-2xl"></i>
            </div>

            <!-- Информация о файле -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <p class="text-sm font-medium text-gray-900 truncate">
                  {{ fileItem.file.name }}
                </p>
                <Tag
                  :value="getFileExtension(fileItem.file.name).toUpperCase()"
                  severity="info"
                  class="text-xs"
                />
              </div>
              <div class="flex items-center gap-4 mt-1">
                <p class="text-xs text-gray-500">
                  {{ formatFileSize(fileItem.file.size) }}
                </p>
                <p v-if="fileItem.wordCount" class="text-xs text-gray-500">
                  {{ fileItem.wordCount }} слов
                </p>
                <p v-if="fileItem.estimatedCost" class="text-xs text-gray-500">
                  ~{{ fileItem.estimatedCost }} кредитов
                </p>
              </div>
            </div>

            <!-- Статус -->
            <div class="flex items-center gap-2">
              <div v-if="fileItem.status === 'pending'" class="flex items-center gap-2">
                <i class="pi pi-clock text-gray-400"></i>
                <span class="text-xs text-gray-500">Ожидание</span>
              </div>
              <div v-else-if="fileItem.status === 'processing'" class="flex items-center gap-2">
                <ProgressSpinner size="small" />
                <span class="text-xs text-blue-600">Обработка...</span>
              </div>
              <div v-else-if="fileItem.status === 'completed'" class="flex items-center gap-2">
                <i class="pi pi-check-circle text-green-500"></i>
                <span class="text-xs text-green-600">Готово</span>
                <Button
                  icon="pi pi-eye"
                  severity="secondary"
                  outlined
                  size="small"
                  @click="viewResult(fileItem.detectionId!)"
                  class="!p-1"
                />
              </div>
              <div v-else-if="fileItem.status === 'error'" class="flex items-center gap-2">
                <i class="pi pi-times-circle text-red-500"></i>
                <span class="text-xs text-red-600">Ошибка</span>
                <Button
                  icon="pi pi-info-circle"
                  severity="danger"
                  outlined
                  size="small"
                  @click="showError(fileItem.error!)"
                  class="!p-1"
                />
              </div>
            </div>

            <!-- Кнопка удаления -->
            <Button
              icon="pi pi-times"
              severity="danger"
              text
              size="small"
              @click="removeFile(index)"
              :disabled="isProcessing && fileItem.status === 'processing'"
              class="!p-1"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Прогресс обработки -->
    <div v-if="isProcessing" class="mt-6 p-4 bg-blue-50 rounded-lg">
      <div class="flex justify-between items-center mb-2">
        <span class="text-sm font-medium text-blue-900">
          Обработка файлов: {{ completedCount }}/{{ files.length }}
        </span>
        <span class="text-sm text-blue-700">
          {{ Math.round((completedCount / files.length) * 100) }}%
        </span>
      </div>
      <div class="w-full bg-blue-200 rounded-full h-2">
        <div
          class="bg-blue-600 h-2 rounded-full transition-all duration-300"
          :style="batchProgressStyle"
        ></div>
      </div>
      <p class="text-xs text-blue-700 mt-2">
        {{ currentProcessingFile ? `Обрабатывается: ${currentProcessingFile}` : 'Подготовка...' }}
      </p>
    </div>

    <!-- Результаты -->
    <div v-if="completedCount > 0 && !isProcessing" class="mt-6 p-4 bg-green-50 rounded-lg">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <i class="pi pi-check-circle text-green-500"></i>
          <span class="text-sm font-medium text-green-900">
            Обработано {{ completedCount }} из {{ files.length }} файлов
          </span>
        </div>
        <div class="flex gap-2">
          <Button label="Перейти к истории" size="small" @click="goToHistory" />
          <Button
            label="Очистить список"
            severity="secondary"
            outlined
            size="small"
            @click="clearAll"
          />
        </div>
      </div>
    </div>
  </div>

  <!-- Диалог ошибки -->
  <Dialog
    v-model:visible="errorDialog"
    modal
    header="Ошибка обработки"
    class="batch-upload-error-dialog"
  >
    <p class="text-sm text-gray-700">{{ currentError }}</p>
    <template #footer>
      <Button label="Закрыть" @click="errorDialog = false" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import Dialog from 'primevue/dialog'
import { useAIDetectionStore } from '../stores/aiDetection'
import { formatFileSize, isValidFileType } from '../services/api'

interface FileItem {
  file: File
  status: 'pending' | 'processing' | 'completed' | 'error'
  detectionId?: number
  error?: string
  wordCount?: number
  estimatedCost?: number
}

const router = useRouter()
const store = useAIDetectionStore()

// Состояние
const files = ref<FileItem[]>([])
const isDragging = ref(false)
const isProcessing = ref(false)
const detailedAnalysis = ref(false)
const fileInput = ref<HTMLInputElement>()
const errorDialog = ref(false)
const currentError = ref('')
const currentProcessingFile = ref('')

// Вычисляемые свойства
const completedCount = computed(() => files.value.filter((f) => f.status === 'completed').length)
const batchProgressPercent = computed(() =>
  files.value.length ? (completedCount.value / files.value.length) * 100 : 0,
)
const batchProgressStyle = computed(() => ({ width: `${batchProgressPercent.value}%` }))

const estimatedCost = computed(() => {
  return files.value.reduce((total, file) => {
    if (file.wordCount) {
      // Примерная стоимость: детальный анализ дороже
      const baseCost = Math.ceil(file.wordCount / 1000)
      return total + (detailedAnalysis.value ? baseCost * 2 : baseCost)
    }
    return total + 1 // Минимальная стоимость если не знаем количество слов
  }, 0)
})

// Методы для работы с файлами
const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = false

  const droppedFiles = Array.from(e.dataTransfer?.files || [])
  addFiles(droppedFiles)
}

const handleFileSelect = (e: Event) => {
  const input = e.target as HTMLInputElement
  const selectedFiles = Array.from(input.files || [])
  addFiles(selectedFiles)

  // Очищаем input для возможности выбора тех же файлов
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const addFiles = async (newFiles: File[]) => {
  // Фильтруем валидные файлы
  const validFiles = newFiles.filter((file) => {
    if (!isValidFileType(file)) {
      console.warn(`Неподдерживаемый тип файла: ${file.name}`)
      return false
    }

    // Проверяем, нет ли уже такого файла
    const exists = files.value.some(
      (item) => item.file.name === file.name && item.file.size === file.size,
    )
    if (exists) {
      console.warn(`Файл уже добавлен: ${file.name}`)
      return false
    }

    return true
  })

  // Ограничиваем до 10 файлов
  const availableSlots = 50 - files.value.length
  const filesToAdd = validFiles.slice(0, availableSlots)

  if (validFiles.length > availableSlots) {
    console.warn(`Можно добавить только ${availableSlots} файлов`)
  }

  // Добавляем файлы и получаем информацию о них
  for (const file of filesToAdd) {
    const fileItem: FileItem = {
      file,
      status: 'pending',
    }

    files.value.push(fileItem)

    // Асинхронно получаем информацию о файле
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/file-info`, {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const info = await response.json()
        fileItem.wordCount = info.word_count
        fileItem.estimatedCost = Math.ceil(info.word_count / 1000)
      }
    } catch (error) {
      console.warn(`Не удалось получить информацию о файле ${file.name}:`, error)
    }
  }
}

const removeFile = (index: number) => {
  files.value.splice(index, 1)
}

const clearAll = () => {
  files.value = []
  isProcessing.value = false
  currentProcessingFile.value = ''
}

// Пакетная обработка
const startBatchAnalysis = async () => {
  if (files.value.length === 0) return

  isProcessing.value = true

  // Сбрасываем статусы
  files.value.forEach((file) => {
    if (file.status !== 'completed') {
      file.status = 'pending'
    }
  })

  // Обрабатываем файлы по очереди
  for (const fileItem of files.value) {
    if (fileItem.status === 'completed') continue

    try {
      fileItem.status = 'processing'
      currentProcessingFile.value = fileItem.file.name

      const result = await store.uploadFile(fileItem.file, detailedAnalysis.value)

      if (result) {
        fileItem.status = 'completed'
        fileItem.detectionId = result.detection_id
      } else {
        fileItem.status = 'error'
        fileItem.error = 'Неизвестная ошибка при обработке файла'
      }
    } catch (error) {
      fileItem.status = 'error'
      fileItem.error = error instanceof Error ? error.message : 'Ошибка обработки'
    }

    // Небольшая пауза между файлами
    await new Promise((resolve) => setTimeout(resolve, 500))
  }

  isProcessing.value = false
  currentProcessingFile.value = ''

  // Обновляем историю
  await store.loadHistory()
}

// Утилиты
const getFileIcon = (file: File): string => {
  const extension = getFileExtension(file.name).toLowerCase()
  switch (extension) {
    case 'pdf':
      return 'pi pi-file-pdf text-red-500'
    case 'docx':
    case 'doc':
      return 'pi pi-file-word text-blue-500'
    case 'txt':
      return 'pi pi-file text-gray-500'
    default:
      return 'pi pi-file text-gray-400'
  }
}

const getFileExtension = (filename: string): string => {
  return filename.split('.').pop() || ''
}

const viewResult = (detectionId: number) => {
  router.push(`/analysis/${detectionId}`)
}

const showError = (error: string) => {
  currentError.value = error
  errorDialog.value = true
}

const goToHistory = () => {
  router.push('/history')
}

// Обработка drag & drop
onMounted(() => {
  document.addEventListener('dragenter', (e) => {
    e.preventDefault()
    isDragging.value = true
  })

  document.addEventListener('dragleave', (e) => {
    if (!e.relatedTarget) {
      isDragging.value = false
    }
  })

  document.addEventListener('drop', (e) => {
    e.preventDefault()
    isDragging.value = false
  })
})
</script>

<style scoped>
:deep(.batch-upload-error-dialog) {
  width: 400px;
}
</style>
