<template>
  <div
    class="ai-indicator"
    :class="indicatorClass"
    v-tooltip.top="detailedTooltip"
  >
    <div class="indicator-icon">
      <svg v-if="isAI" class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 2L13.09 8.26L20 9L13.09 9.74L12 16L10.91 9.74L4 9L10.91 8.26L12 2Z" />
      </svg>
      <svg v-else class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
        <path
          d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"
        />
      </svg>
    </div>
    <span class="indicator-text">{{ percentage }}%</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  aiLikelihood: number
  size?: 'small' | 'medium' | 'large'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'small',
})

const percentage = computed(() => Math.round(props.aiLikelihood * 100))
const isAI = computed(() => percentage.value >= 50)

const indicatorClass = computed(() => {
  const sizeClass = {
    small: 'text-xs px-1.5 py-0.5',
    medium: 'text-sm px-2 py-1',
    large: 'text-base px-3 py-1.5',
  }[props.size]

  let colorClass = ''
  if (percentage.value >= 80) {
    colorClass = 'bg-red-600 text-white border-red-700'
  } else if (percentage.value >= 50) {
    colorClass = 'bg-orange-600 text-white border-orange-700'
  } else if (percentage.value >= 20) {
    colorClass = 'bg-yellow-600 text-white border-yellow-700'
  } else {
    colorClass = 'bg-green-600 text-white border-green-700'
  }

  return `${sizeClass} ${colorClass}`
})

const detailedTooltip = computed(() => {
  const type = isAI.value ? 'ИИ' : 'Человек'
  let confidence = ''

  if (percentage.value >= 90) {
    confidence = 'Очень высокая уверенность'
  } else if (percentage.value >= 70) {
    confidence = 'Высокая уверенность'
  } else if (percentage.value >= 50) {
    confidence = 'Средняя уверенность'
  } else if (percentage.value >= 30) {
    confidence = 'Низкая уверенность'
  } else {
    confidence = 'Очень низкая уверенность'
  }

  let description = ''
  if (percentage.value >= 80) {
    description = 'Текст скорее всего создан искусственным интеллектом'
  } else if (percentage.value >= 50) {
    description = 'Высокая вероятность использования ИИ при создании текста'
  } else if (percentage.value >= 20) {
    description = 'Возможно частичное использование ИИ'
  } else {
    description = 'Текст вероятно написан человеком'
  }

  return `${type}: ${percentage.value}%\n${confidence}\n${description}`
})
</script>

<style scoped>
.ai-indicator {
  @apply inline-flex items-center gap-1 rounded-full font-medium cursor-help transition-all duration-300 border;
  animation: pulse-glow 2s ease-in-out infinite;
}

.ai-indicator:hover {
  @apply scale-110 shadow-lg;
  animation: none;
}

.indicator-icon {
  @apply flex items-center justify-center;
}

.indicator-text {
  @apply font-bold;
}

@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 0 0 5px rgba(0, 0, 0, 0.1);
  }
  50% {
    box-shadow: 0 0 15px rgba(0, 0, 0, 0.2);
  }
}

/* Специальные эффекты для высокой вероятности ИИ */
.ai-indicator:has(.bg-red-600) {
  animation: danger-pulse 1.5s ease-in-out infinite;
}

@keyframes danger-pulse {
  0%, 100% {
    box-shadow: 0 0 5px rgba(220, 38, 38, 0.3);
  }
  50% {
    box-shadow: 0 0 20px rgba(220, 38, 38, 0.6);
  }
}
</style>
