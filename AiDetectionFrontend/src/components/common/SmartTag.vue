<template>
  <Tag
    :value="value"
    :severity="severity"
    :class="tagClass"
    v-tooltip.top="computedTooltip"
    v-bind="$attrs"
  >
    <template v-if="$slots.default">
      <slot />
    </template>
  </Tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Tag from 'primevue/tag'

interface Props {
  value: string
  severity?: 'success' | 'info' | 'warning' | 'danger' | 'secondary'
  type?: 'ai-likelihood' | 'plagiarism' | 'file-type' | 'prediction' | 'custom'
  tooltip?: string
  aiLikelihood?: number
  originality?: number
  tagClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  severity: 'info',
  type: 'custom',
  tagClass: '',
})

const computedTooltip = computed(() => {
  if (props.tooltip) return props.tooltip

  switch (props.type) {
    case 'ai-likelihood':
      if (props.aiLikelihood !== undefined) {
        const percentage = Math.round(props.aiLikelihood * 100)
        let description = ''
        if (percentage >= 80) description = 'Текст скорее всего создан ИИ'
        else if (percentage >= 50) description = 'Высокая вероятность использования ИИ'
        else if (percentage >= 20) description = 'Возможно частичное использование ИИ'
        else description = 'Текст вероятно написан человеком'
        return `Вероятность ИИ: ${percentage}%. ${description}`
      }
      return 'Вероятность того, что текст был создан искусственным интеллектом'

    case 'plagiarism':
      if (props.originality !== undefined) {
        const percentage = Math.round(props.originality)
        let description = ''
        if (percentage >= 85) description = 'Отличная оригинальность, плагиат не обнаружен'
        else if (percentage >= 70) description = 'Хорошая оригинальность, незначительные совпадения'
        else if (percentage >= 50) description = 'Средняя оригинальность, есть подозрительные фрагменты'
        else description = 'Низкая оригинальность, обнаружен значительный плагиат'
        return `Оригинальность: ${percentage}%. ${description}`
      }
      return 'Процент оригинального (неплагиатного) содержимого'

    case 'file-type':
      return `Тип файла: ${props.value}`

    case 'prediction':
      return `Результат анализа: ${props.value}`

    default:
      return props.value
  }
})
</script>

<style scoped>
:deep(.p-tag) {
  cursor: help;
  transition: all 0.2s ease;
}

:deep(.p-tag:hover) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
</style>
