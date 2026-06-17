<template>
  <section v-if="entries.length" class="va-card llm-prediction-card">
    <header class="llm-prediction-card__header">
      <div>
        <p class="llm-prediction-card__eyebrow">Вероятные модели</p>
        <h3 class="llm-prediction-card__title">Модельный след</h3>
      </div>
      <span class="llm-prediction-card__top">{{ entries[0].label }}</span>
    </header>

    <div class="llm-prediction-card__list">
      <div v-for="entry in entries" :key="entry.key" class="llm-prediction-card__row">
        <div class="llm-prediction-card__row-head">
          <span class="llm-prediction-card__model">{{ entry.label }}</span>
          <span class="tnum llm-prediction-card__value">{{ formatScore(entry.score) }}</span>
        </div>
        <div class="llm-prediction-card__track">
          <span class="llm-prediction-card__fill" :style="{ width: `${Math.max(entry.score * 100, 1.5)}%` }" />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  prediction?: Record<string, number>
}>()

const modelLabels: Record<string, string> = {
  GPT35: 'GPT-3.5',
  GPT4: 'GPT-4',
  CLAUDE: 'Claude',
  GOOGLE: 'Google',
  OPENAI_O_SERIES: 'OpenAI o-series',
  DEEPSEEK: 'DeepSeek',
  GROK: 'Grok',
  NOVA: 'Nova',
  OTHER: 'Другое',
  HUMAN: 'Человек',
}

const clampScore = (value: unknown) => {
  const numeric = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(numeric)) return 0
  return Math.min(1, Math.max(0, numeric))
}

const entries = computed(() =>
  Object.entries(props.prediction ?? {})
    .map(([key, value]) => ({
      key,
      label: modelLabels[key] ?? key,
      score: clampScore(value),
    }))
    .sort((left, right) => right.score - left.score),
)

const formatScore = (value: number) => {
  if (value > 0 && value < 0.001) return '<0,1%'
  return `${(value * 100).toLocaleString('ru-RU', {
    maximumFractionDigits: value >= 0.1 ? 1 : 2,
  })}%`
}
</script>

<style scoped>
.llm-prediction-card {
  display: grid;
  gap: 14px;
  padding: 18px;
}

.llm-prediction-card__header {
  align-items: flex-start;
  display: flex;
  gap: 12px;
  justify-content: space-between;
  min-width: 0;
}

.llm-prediction-card__eyebrow {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  margin: 0 0 3px;
  text-transform: uppercase;
}

.llm-prediction-card__title {
  color: var(--ink);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.2;
  margin: 0;
}

.llm-prediction-card__top {
  background: var(--mixed-bg);
  border: 1px solid var(--mixed-bg-hi);
  border-radius: 999px;
  color: var(--mixed-ink);
  flex: 0 0 auto;
  font-size: 11px;
  font-weight: 800;
  max-width: 45%;
  overflow: hidden;
  padding: 5px 8px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.llm-prediction-card__list {
  display: grid;
  gap: 10px;
}

.llm-prediction-card__row {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.llm-prediction-card__row-head {
  align-items: center;
  display: flex;
  gap: 10px;
  justify-content: space-between;
  min-width: 0;
}

.llm-prediction-card__model {
  color: var(--ink-2);
  font-size: 12px;
  font-weight: 650;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.llm-prediction-card__value {
  color: var(--ink);
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 800;
}

.llm-prediction-card__track {
  background: var(--bg-sunken);
  border-radius: 999px;
  height: 6px;
  overflow: hidden;
}

.llm-prediction-card__fill {
  background: linear-gradient(90deg, var(--mixed), var(--ai));
  border-radius: inherit;
  display: block;
  height: 100%;
  max-width: 100%;
}
</style>
