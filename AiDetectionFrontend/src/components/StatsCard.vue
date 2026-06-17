<template>
  <div class="bg-white rounded-lg shadow-lg p-6">
    <div class="mb-4">
      <h2 class="text-xl font-bold text-black">Статистика</h2>
    </div>

    <div v-if="stats" class="space-y-4">
      <!-- Общие метрики -->
      <div class="grid grid-cols-2 gap-4">
        <div class="bg-blue-50 rounded-lg p-4 border border-blue-200">
          <div class="text-sm font-medium text-blue-600">Всего анализов</div>
          <div class="text-2xl font-bold text-black">{{ stats.total_analyses }}</div>
        </div>

        <div class="bg-green-50 rounded-lg p-4 border border-green-200">
          <div class="text-sm font-medium text-green-600">Средняя вероятность ИИ</div>
          <div class="text-2xl font-bold text-black">
            {{ formatPercentage(stats.avg_ai_likelihood) }}
          </div>
        </div>
      </div>

      <!-- Детальная статистика -->
      <div class="grid grid-cols-3 gap-4">
        <div class="bg-red-50 rounded-lg p-4 border border-red-200">
          <div class="text-sm font-medium text-red-600">ИИ контент</div>
          <div class="text-xl font-bold text-black">{{ stats.ai_generated }}</div>
          <div class="text-xs text-red-500">{{ stats.ai_percentage }}%</div>
        </div>

        <div class="bg-green-50 rounded-lg p-4 border border-green-200">
          <div class="text-sm font-medium text-green-600">Человек</div>
          <div class="text-xl font-bold text-black">{{ stats.human_generated }}</div>
          <div class="text-xs text-green-500">{{ Math.round(100 - stats.ai_percentage) }}%</div>
        </div>

        <div class="bg-blue-50 rounded-lg p-4 border border-blue-200">
          <div class="text-sm font-medium text-blue-600">За неделю</div>
          <div class="text-xl font-bold text-black">{{ stats.recent_analyses }}</div>
        </div>
      </div>
    </div>

    <!-- Состояние загрузки -->
    <div v-else class="text-center py-8">
      <ProgressSpinner />
      <p class="text-gray-500 mt-4">Загрузка статистики...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { useAIDetectionStore } from '../stores/aiDetection'

const store = useAIDetectionStore()
const { stats } = storeToRefs(store)

// Методы
const loadStats = async () => {
  await store.loadStats()
}

const formatPercentage = (value: number): string => {
  return `${Math.round(value * 100)}%`
}

// Загружаем статистику при монтировании
onMounted(() => {
  loadStats()
})
</script>
