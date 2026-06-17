<template>
  <div class="min-h-screen bg-gray-50 py-8">
    <div class="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <!-- Навигация -->
      <AppNavigation
        title="Управление датасетом"
        description="Просмотр и экспорт данных для обучения модели детекции ИИ"
      >
        <template #actions>
          <Button
            @click="refreshStatus"
            :loading="loading.status"
            icon="pi pi-refresh"
            label="Обновить"
            outlined
            class="bg-white hover:bg-gray-50"
          />
        </template>
      </AppNavigation>

      <!-- Основной контент -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Статистика датасета -->
        <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div class="flex items-center gap-3 mb-6">
            <div class="p-3 bg-blue-100 rounded-lg">
              <i class="pi pi-database text-blue-600 text-xl"></i>
            </div>
            <div>
              <h3 class="text-xl font-semibold text-gray-900">Статистика датасета</h3>
              <p class="text-gray-600 text-sm">Информация о накопленных данных</p>
            </div>
          </div>

          <div class="space-y-6">
            <!-- Основные метрики -->
            <div class="grid grid-cols-2 gap-4">
              <div class="text-center p-4 bg-gray-50 rounded-lg">
                <div class="text-3xl font-bold text-blue-600 mb-1">
                  {{ datasetStats.total_samples || 0 }}
                </div>
                <div class="text-sm text-gray-600">Всего образцов</div>
              </div>
              <div class="text-center p-4 bg-gray-50 rounded-lg">
                <div class="text-3xl font-bold text-green-600 mb-1">
                  {{ datasetStats.recent_samples_30d || 0 }}
                </div>
                <div class="text-sm text-gray-600">За последний месяц</div>
              </div>
            </div>

            <!-- Статус готовности -->
            <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <div class="font-medium text-gray-900">Готовность к обучению</div>
                <div class="text-sm text-gray-600">Достаточно ли данных для модели</div>
              </div>
              <Tag
                :value="datasetStats.ready_for_training ? 'Готов' : 'Не готов'"
                :severity="datasetStats.ready_for_training ? 'success' : 'warning'"
                class="font-medium"
              />
            </div>
          </div>
        </div>

        <!-- Распределение данных -->
        <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div class="flex items-center gap-3 mb-6">
            <div class="p-3 bg-green-100 rounded-lg">
              <i class="pi pi-chart-pie text-green-600 text-xl"></i>
            </div>
            <div>
              <h3 class="text-xl font-semibold text-gray-900">Распределение данных</h3>
              <p class="text-gray-600 text-sm">Баланс между классами</p>
            </div>
          </div>

          <div v-if="datasetStats.distribution" class="space-y-4">
            <div
              v-for="(count, category) in datasetStats.distribution"
              :key="category"
              class="flex items-center justify-between"
            >
              <div class="flex items-center gap-3">
                <div class="w-4 h-4 rounded" :class="getCategoryColor(category)"></div>
                <span class="font-medium text-gray-900">{{ getCategoryLabel(category) }}</span>
              </div>
              <div class="text-right">
                <div class="font-bold text-gray-900">{{ count }}</div>
                <div class="text-xs text-gray-500">
                  {{ Math.round((count / (datasetStats.total_samples || 1)) * 100) }}%
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-8 text-gray-500">
            <i class="pi pi-chart-pie text-4xl mb-4"></i>
            <p>Нет данных для отображения</p>
          </div>
        </div>

        <!-- Экспорт данных -->
        <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200 lg:col-span-2">
          <div class="flex items-center gap-3 mb-6">
            <div class="p-3 bg-purple-100 rounded-lg">
              <i class="pi pi-download text-purple-600 text-xl"></i>
            </div>
            <div>
              <h3 class="text-xl font-semibold text-gray-900">Экспорт данных</h3>
              <p class="text-gray-600 text-sm">Скачайте данные в различных форматах</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="border border-gray-200 rounded-lg p-4">
              <div class="flex items-center gap-3 mb-3">
                <i class="pi pi-file-export text-2xl text-blue-600"></i>
                <div>
                  <h4 class="font-medium text-gray-900">JSON формат</h4>
                  <p class="text-sm text-gray-600">Структурированные данные для разработки</p>
                </div>
              </div>
              <Button
                @click="exportDataset('json')"
                :loading="loading.export"
                icon="pi pi-download"
                label="Скачать JSON"
                class="w-full"
                severity="info"
              />
            </div>

            <div class="border border-gray-200 rounded-lg p-4">
              <div class="flex items-center gap-3 mb-3">
                <i class="pi pi-file-excel text-2xl text-green-600"></i>
                <div>
                  <h4 class="font-medium text-gray-900">CSV формат</h4>
                  <p class="text-sm text-gray-600">Табличные данные для анализа</p>
                </div>
              </div>
              <Button
                @click="exportDataset('csv')"
                :loading="loading.export"
                icon="pi pi-download"
                label="Скачать CSV"
                class="w-full"
                severity="success"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import { AppNavigation } from '../components/common'

const toast = useToast()

// Состояние загрузки
const loading = ref({
  status: false,
  export: false,
})

// Статистика датасета
const datasetStats = ref({
  total_samples: 0,
  recent_samples_30d: 0,
  ready_for_training: false,
  distribution: {} as Record<string, number>,
})

// Методы
const refreshStatus = async () => {
  loading.value.status = true
  try {
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/detector/dataset/stats`)

    if (response.ok) {
      const data = await response.json()
      datasetStats.value = data
    } else {
      throw new Error('Ошибка загрузки статистики')
    }
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Ошибка',
      detail: 'Не удалось загрузить статистику датасета',
    })
  } finally {
    loading.value.status = false
  }
}

const exportDataset = async (format: string = 'csv') => {
  loading.value.export = true
  try {
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/detector/dataset/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        format: format,
        include_text: true,
        min_likelihood: 0.0,
      }),
    })

    const result = await response.json()

    if (response.ok) {
      // Убираем тост - он не нужен, так как файл скачивается автоматически

      // Скачиваем файл
      if (result.download_url) {
        const downloadUrl = `${import.meta.env.VITE_API_BASE_URL}${result.download_url}`
        const downloadLink = document.createElement('a')
        downloadLink.href = downloadUrl
        downloadLink.download = result.filename
        downloadLink.target = '_blank'
        document.body.appendChild(downloadLink)
        downloadLink.click()
        document.body.removeChild(downloadLink)
      }
    } else {
      throw new Error(result.error)
    }
  } catch (error: unknown) {
    toast.add({
      severity: 'error',
      summary: 'Ошибка экспорта',
      detail: error instanceof Error ? error.message : 'Неизвестная ошибка',
    })
  } finally {
    loading.value.export = false
  }
}

const getCategoryLabel = (category: string): string => {
  const labels: Record<string, string> = {
    high_ai: 'Высокий ИИ',
    medium_ai: 'Средний ИИ',
    mixed: 'Смешанный',
    medium_human: 'Средний человек',
    high_human: 'Высокий человек',
  }
  return labels[category] || category
}

const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    high_ai: 'bg-red-500',
    medium_ai: 'bg-orange-500',
    mixed: 'bg-yellow-500',
    medium_human: 'bg-blue-500',
    high_human: 'bg-green-500',
  }
  return colors[category] || 'bg-gray-500'
}

// Инициализация
onMounted(() => {
  refreshStatus()
})
</script>

<style scoped>
.detector-page {
  min-height: 100vh;
  background-color: #f9fafb;
}
</style>
