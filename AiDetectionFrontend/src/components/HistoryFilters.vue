<template>
  <div class="bg-white rounded-xl shadow-lg border border-gray-100 p-6 mb-6">
    <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-6 gap-4">
      <h3 class="text-xl font-bold text-gray-900">Фильтры</h3>
      <div class="flex gap-3">
        <Button
          @click="applyFilters"
          icon="pi pi-search"
          label="Применить"
          :disabled="isLoading"
          class="bg-green-600 hover:bg-green-700 text-white border-0 px-6 py-2 rounded-lg font-medium"
        />
        <Button
          @click="clearAllFilters"
          icon="pi pi-refresh"
          label="Сбросить"
          outlined
          :disabled="isLoading"
          class="border-gray-300 text-gray-700 hover:bg-gray-50 px-6 py-2 rounded-lg font-medium"
        />
      </div>
    </div>

    <!-- Детальные фильтры -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <!-- Поиск -->
      <div class="filter-field">
        <label class="filter-label">
          <i class="pi pi-search text-blue-500 mr-2"></i>
          Поиск по названию
        </label>
        <InputText
          v-model="localFilters.search"
          placeholder="Введите название файла..."
          class="filter-input"
        />
      </div>

      <!-- Тип файла -->
      <div class="filter-field">
        <label class="filter-label">
          <i class="pi pi-file text-purple-500 mr-2"></i>
          Тип файла
        </label>
        <Dropdown
          v-model="localFilters.fileType"
          :options="fileTypeOptions"
          option-label="label"
          option-value="value"
          placeholder="Все типы"
          class="filter-dropdown"
          show-clear
        />
      </div>

      <!-- Предсказание -->
      <div class="filter-field">
        <label class="filter-label">
          <i class="pi pi-chart-line text-green-500 mr-2"></i>
          Предсказание
        </label>
        <Dropdown
          v-model="localFilters.prediction"
          :options="predictionOptions"
          option-label="label"
          option-value="value"
          placeholder="Все предсказания"
          class="filter-dropdown"
          show-clear
        />
      </div>

      <!-- Дата от -->
      <div class="filter-field">
        <label class="filter-label">
          <i class="pi pi-calendar text-orange-500 mr-2"></i>
          Дата от
        </label>
        <Calendar
          v-model="dateFrom"
          date-format="dd.mm.yy"
          placeholder="Выберите дату"
          class="filter-calendar"
          show-clear
        />
      </div>

      <!-- Дата до -->
      <div class="filter-field">
        <label class="filter-label">
          <i class="pi pi-calendar text-orange-500 mr-2"></i>
          Дата до
        </label>
        <Calendar
          v-model="dateTo"
          date-format="dd.mm.yy"
          placeholder="Выберите дату"
          class="filter-calendar"
          show-clear
        />
      </div>

      <!-- Вероятность ИИ -->
      <div class="filter-field">
        <label class="filter-label">
          <i class="pi pi-sliders-h text-red-500 mr-2"></i>
          Вероятность ИИ:
          {{ formatRange(localFilters.aiLikelihoodMin, localFilters.aiLikelihoodMax) }}
        </label>
        <div class="slider-container">
          <Slider
            v-model="aiLikelihoodRange"
            :min="0"
            :max="100"
            :step="5"
            range
            class="custom-slider"
          />
        </div>
      </div>
    </div>

    <!-- Активные фильтры -->
    <div v-if="hasActiveFilters" class="mt-4 pt-4 border-t border-gray-200">
      <div class="flex flex-wrap gap-2">
        <span class="text-sm font-medium text-gray-600 mr-2">Активные фильтры:</span>

        <Tag
          v-if="localFilters.search"
          :value="'Поиск: ' + localFilters.search"
          severity="info"
          removable
          @remove="localFilters.search = ''"
          v-tooltip.top="`Поиск по названию файла: '${localFilters.search}'`"
        />

        <Tag
          v-if="localFilters.fileType"
          :value="'Тип: ' + getFileTypeLabel(localFilters.fileType)"
          severity="info"
          removable
          @remove="localFilters.fileType = ''"
          v-tooltip.top="`Фильтр по типу файла: ${getFileTypeLabel(localFilters.fileType)}`"
        />

        <Tag
          v-if="localFilters.prediction"
          :value="'Предсказание: ' + getPredictionLabel(localFilters.prediction)"
          severity="info"
          removable
          @remove="localFilters.prediction = ''"
          v-tooltip.top="
            `Фильтр по типу предсказания: ${getPredictionLabel(localFilters.prediction)}`
          "
        />

        <Tag
          v-if="localFilters.dateFrom"
          :value="'От: ' + formatDate(localFilters.dateFrom)"
          severity="info"
          removable
          @remove="clearDateFrom"
          v-tooltip.top="`Показать анализы начиная с: ${formatDate(localFilters.dateFrom)}`"
        />

        <Tag
          v-if="localFilters.dateTo"
          :value="'До: ' + formatDate(localFilters.dateTo)"
          severity="info"
          removable
          @remove="clearDateTo"
          v-tooltip.top="`Показать анализы до: ${formatDate(localFilters.dateTo)}`"
        />

        <Tag
          v-if="hasAILikelihoodFilter"
          :value="'ИИ: ' + formatRange(localFilters.aiLikelihoodMin, localFilters.aiLikelihoodMax)"
          severity="info"
          removable
          @remove="clearAILikelihoodFilter"
          v-tooltip.top="
            `Фильтр по вероятности ИИ: ${formatRange(localFilters.aiLikelihoodMin, localFilters.aiLikelihoodMax)}`
          "
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Calendar from 'primevue/calendar'
import Slider from 'primevue/slider'
import Tag from 'primevue/tag'
import { useAIDetectionStore } from '../stores/aiDetection'
import type { HistoryFilters, FilterOption } from '../types/api'

const store = useAIDetectionStore()
const { isLoading, filters } = storeToRefs(store)

// Локальные фильтры для формы
const localFilters = ref<HistoryFilters>({ ...filters.value })

// Убрано состояние сворачивания - фильтры всегда видны

// Даты для календаря
const dateFrom = ref<Date | null>(null)
const dateTo = ref<Date | null>(null)

// Диапазон вероятности ИИ
const aiLikelihoodRange = ref<[number, number]>([0, 100])

// Опции для выпадающих списков
const fileTypeOptions: FilterOption[] = [
  { label: 'PDF', value: 'pdf' },
  { label: 'Word (DOCX)', value: 'docx' },
  { label: 'Word (DOC)', value: 'doc' },
  { label: 'Текст (TXT)', value: 'txt' },
  { label: 'Текстовый ввод', value: 'text' },
]

const predictionOptions: FilterOption[] = [
  { label: 'ИИ', value: 'AI' },
  { label: 'Человек', value: 'HUMAN' },
]

// Computed
const hasActiveFilters = computed(() => {
  return !!(
    localFilters.value.search ||
    localFilters.value.fileType ||
    localFilters.value.prediction ||
    localFilters.value.dateFrom ||
    localFilters.value.dateTo ||
    localFilters.value.aiLikelihoodMin !== undefined ||
    localFilters.value.aiLikelihoodMax !== undefined
  )
})

const hasAILikelihoodFilter = computed(() => {
  return (
    localFilters.value.aiLikelihoodMin !== undefined ||
    localFilters.value.aiLikelihoodMax !== undefined
  )
})

// Методы
const applyFilters = async () => {
  await store.applyFilters(localFilters.value)
}

const clearAllFilters = async () => {
  localFilters.value = {}
  dateFrom.value = null
  dateTo.value = null
  aiLikelihoodRange.value = [0, 100]
  await store.clearFilters()
  await store.loadHistory(1)
}

const clearDateFrom = () => {
  localFilters.value.dateFrom = ''
  dateFrom.value = null
}

const clearDateTo = () => {
  localFilters.value.dateTo = ''
  dateTo.value = null
}

const clearAILikelihoodFilter = () => {
  localFilters.value.aiLikelihoodMin = undefined
  localFilters.value.aiLikelihoodMax = undefined
  aiLikelihoodRange.value = [0, 100]
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('ru-RU')
}

const formatRange = (min?: number, max?: number): string => {
  if (min === undefined && max === undefined) return '0-100%'
  if (min !== undefined && max !== undefined) {
    return `${Math.round(min * 100)}-${Math.round(max * 100)}%`
  }
  if (min !== undefined) return `от ${Math.round(min * 100)}%`
  if (max !== undefined) return `до ${Math.round(max * 100)}%`
  return '0-100%'
}

const getFileTypeLabel = (value: string): string => {
  const option = fileTypeOptions.find((opt) => opt.value === value)
  return option?.label || value
}

const getPredictionLabel = (value: string): string => {
  const option = predictionOptions.find((opt) => opt.value === value)
  return option?.label || value
}

// Watchers
watch(dateFrom, (newDate) => {
  localFilters.value.dateFrom = newDate ? newDate.toISOString().split('T')[0] : ''
})

watch(dateTo, (newDate) => {
  localFilters.value.dateTo = newDate ? newDate.toISOString().split('T')[0] : ''
})

watch(aiLikelihoodRange, ([min, max]) => {
  if (min > 0 || max < 100) {
    localFilters.value.aiLikelihoodMin = min / 100
    localFilters.value.aiLikelihoodMax = max / 100
  } else {
    localFilters.value.aiLikelihoodMin = undefined
    localFilters.value.aiLikelihoodMax = undefined
  }
})

// Инициализация при загрузке существующих фильтров
watch(
  filters,
  (newFilters) => {
    localFilters.value = { ...newFilters }

    if (newFilters.dateFrom) {
      dateFrom.value = new Date(newFilters.dateFrom)
    }

    if (newFilters.dateTo) {
      dateTo.value = new Date(newFilters.dateTo)
    }

    if (newFilters.aiLikelihoodMin !== undefined || newFilters.aiLikelihoodMax !== undefined) {
      const min = newFilters.aiLikelihoodMin ? Math.round(newFilters.aiLikelihoodMin * 100) : 0
      const max = newFilters.aiLikelihoodMax ? Math.round(newFilters.aiLikelihoodMax * 100) : 100
      aiLikelihoodRange.value = [min, max]
    }
  },
  { immediate: true },
)
</script>

<style scoped>
/* Стили для полей фильтров */
.filter-field {
  @apply space-y-3;
}

.filter-label {
  @apply flex items-center text-sm font-semibold text-gray-700 mb-2;
}

/* Стили для инпутов */
.filter-input {
  @apply w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 bg-gray-50 hover:bg-white;
}

/* Стили для дропдаунов */
:deep(.filter-dropdown) {
  @apply w-full;
}

:deep(.filter-dropdown .p-dropdown) {
  @apply w-full border-gray-200 rounded-lg bg-gray-50 hover:bg-white transition-all duration-200;
}

:deep(.filter-dropdown .p-dropdown:not(.p-disabled):hover) {
  @apply border-gray-300;
}

:deep(.filter-dropdown .p-dropdown:not(.p-disabled).p-focus) {
  @apply ring-2 ring-blue-500 border-blue-500 bg-white;
}

:deep(.filter-dropdown .p-dropdown-label) {
  @apply px-4 py-3 text-gray-700;
}

:deep(.filter-dropdown .p-dropdown-trigger) {
  @apply px-3;
}

/* Стили для календаря */
:deep(.filter-calendar) {
  @apply w-full;
}

:deep(.filter-calendar .p-calendar .p-inputtext) {
  @apply w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 bg-gray-50 hover:bg-white;
}

/* Стили для слайдера */
.slider-container {
  @apply mt-4 px-2;
}

:deep(.custom-slider .p-slider) {
  @apply bg-gray-200 h-2 rounded-full;
}

:deep(.custom-slider .p-slider .p-slider-range) {
  @apply bg-gradient-to-r from-blue-500 to-green-500 h-2 rounded-full;
}

:deep(.custom-slider .p-slider .p-slider-handle) {
  @apply w-5 h-5 bg-white border-2 border-blue-500 rounded-full shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-110;
}

:deep(.custom-slider .p-slider .p-slider-handle:focus) {
  @apply ring-2 ring-blue-500 ring-opacity-50;
}

/* Стили для тегов активных фильтров */
:deep(.p-tag) {
  @apply bg-blue-100 text-blue-800 border border-blue-200 rounded-lg px-3 py-1 text-sm font-medium;
}

:deep(.p-tag .p-tag-icon) {
  @apply ml-2 text-blue-600 hover:text-blue-800 cursor-pointer;
}

/* Стили для светлой темы компонентов PrimeVue */
:deep(.p-dropdown) {
  background-color: white !important;
  border: 1px solid #d1d5db !important;
}

:deep(.p-dropdown .p-dropdown-label) {
  background-color: white !important;
  color: #374151 !important;
}

:deep(.p-dropdown .p-dropdown-label.p-placeholder) {
  color: #6b7280 !important;
}

:deep(.p-dropdown:not(.p-disabled):hover) {
  border-color: #9ca3af !important;
}

:deep(.p-dropdown:not(.p-disabled).p-focus) {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 1px #3b82f6 !important;
}

:deep(.p-dropdown-panel) {
  background-color: white !important;
  border: 1px solid #d1d5db !important;
}

:deep(.p-dropdown-items .p-dropdown-item) {
  background-color: white !important;
  color: #374151 !important;
}

:deep(.p-dropdown-items .p-dropdown-item:hover) {
  background-color: #f3f4f6 !important;
  color: #374151 !important;
}

:deep(.p-dropdown-items .p-dropdown-item.p-highlight) {
  background-color: #3b82f6 !important;
  color: white !important;
}

/* Стили для Calendar */
:deep(.p-calendar) {
  background-color: white !important;
}

:deep(.p-calendar .p-inputtext) {
  background-color: white !important;
  color: #374151 !important;
  border: 1px solid #d1d5db !important;
}

:deep(.p-calendar .p-inputtext:hover) {
  border-color: #9ca3af !important;
}

:deep(.p-calendar .p-inputtext:focus) {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 1px #3b82f6 !important;
}

/* Стили для InputText */
:deep(.p-inputtext) {
  background-color: white !important;
  color: #374151 !important;
  border: 1px solid #d1d5db !important;
}

:deep(.p-inputtext:hover) {
  border-color: #9ca3af !important;
}

:deep(.p-inputtext:focus) {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 1px #3b82f6 !important;
}

/* Стили для Slider */
:deep(.p-slider) {
  background-color: #e5e7eb !important;
}

:deep(.p-slider .p-slider-range) {
  background-color: #3b82f6 !important;
}

:deep(.p-slider .p-slider-handle) {
  background-color: #3b82f6 !important;
  border: 2px solid #3b82f6 !important;
}

:deep(.p-slider .p-slider-handle:hover) {
  background-color: #2563eb !important;
  border-color: #2563eb !important;
}
</style>
