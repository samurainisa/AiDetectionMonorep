<template>
  <div v-if="show" class="ai-detection-banner bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <!-- Иконка предупреждения -->
        <div class="flex-shrink-0">
          <div class="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
            <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
              ></path>
            </svg>
          </div>
        </div>

        <!-- Текст -->
        <div>
          <h3 class="text-lg font-bold text-red-800">AI Detected</h3>
          <p class="text-red-700">Искусственный интеллект обнаружен в тексте</p>
        </div>

        <!-- Статистика -->
        <div class="flex space-x-6 ml-8">
          <div class="text-center">
            <div class="text-2xl font-bold text-red-600">{{ aiSegments }}/{{ totalSegments }}</div>
            <div class="text-xs text-red-500 uppercase tracking-wide">AI сегменты</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-red-600">{{ confidence }}%</div>
            <div class="text-xs text-red-500 uppercase tracking-wide">Уверенность</div>
          </div>
        </div>
      </div>

      <!-- Кнопка закрытия -->
      <button @click="$emit('close')" class="text-red-500 hover:text-red-700 transition-colors">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M6 18L18 6M6 6l12 12"
          ></path>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  show: boolean
  aiSegments: number
  totalSegments: number
  confidence: number
}

interface Emits {
  (e: 'close'): void
}

defineProps<Props>()
defineEmits<Emits>()
</script>

<style scoped>
.ai-detection-banner {
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
