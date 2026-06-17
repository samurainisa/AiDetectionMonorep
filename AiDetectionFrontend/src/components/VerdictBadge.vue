<template>
  <span class="va-chip verdict-badge" :class="[cls, sizeClass]">
    <span class="va-dot" :class="cls" />
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    verdict: string
    size?: 'md' | 'lg'
  }>(),
  { size: 'md' },
)

const verdictMap: Record<string, { label: string; cls: string }> = {
  ai: { label: 'Сгенерировано ИИ', cls: 'ai' },
  human: { label: 'Написано человеком', cls: 'human' },
  mixed: { label: 'Смешанный контент', cls: 'mixed' },
}

const verdictMeta = computed(() => verdictMap[props.verdict] ?? verdictMap.mixed)
const cls = computed(() => verdictMeta.value.cls)
const label = computed(() => verdictMeta.value.label)
const sizeClass = computed(() => (props.size === 'lg' ? 'verdict-badge--lg' : 'verdict-badge--md'))
</script>

<style scoped>
.verdict-badge {
  gap: 5px;
  white-space: nowrap;
}

.verdict-badge--md {
  font-size: 11px;
  height: 22px;
  padding: 0 8px;
}

.verdict-badge--lg {
  font-size: 12px;
  height: 30px;
  padding: 0 10px;
}
</style>
