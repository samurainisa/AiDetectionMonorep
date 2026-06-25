<template>
  <section v-if="rawEntries.length" class="va-card llm-prediction-card">
    <header class="llm-prediction-card__header">
      <div>
        <p class="llm-prediction-card__eyebrow">Вероятные модели</p>
        <h3 class="llm-prediction-card__title">Атрибуция модели</h3>
      </div>
      <span class="llm-prediction-card__top" :class="{ 'llm-prediction-card__top--muted': !hasConfidentMatch }">
        {{ topLabel }}
      </span>
    </header>

    <div class="llm-prediction-card__options" aria-label="Опции модельного поиска">
      <span>{{ endpointLabel }}</span>
      <span>Все модели</span>
      <span>Порог 0,1%</span>
    </div>

    <div v-if="label || aiLikelihood != null" class="llm-prediction-card__summary">
      <span v-if="label">{{ localizedLabel }}</span>
      <span v-if="aiLikelihood != null" class="tnum">{{ formatScore(aiLikelihood) }} след</span>
    </div>

    <p class="llm-prediction-card__note">
      Отдельный модельный поиск: показывает, на какую LLM похож текст. Это не доля ИИ в документе.
    </p>

    <p v-if="requestId" class="llm-prediction-card__request">ID запроса: {{ requestId }}</p>

    <p v-if="!hasConfidentMatch" class="llm-prediction-card__empty">
      Сервис атрибуции не нашёл уверенного следа конкретной модели. Это не означает 0% ИИ в основном результате.
    </p>

    <div v-else class="llm-prediction-card__list">
      <div v-for="entry in visibleEntries" :key="entry.key" class="llm-prediction-card__row">
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
import { localizePredictionText } from '../utils/aiResult'

const props = defineProps<{
  prediction?: Record<string, number>
  label?: string
  aiLikelihood?: number
  source?: string
  requestId?: string
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
  HUMANIZER: 'Humanizer',
}

const clampScore = (value: unknown) => {
  const numeric = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(numeric)) return 0
  return Math.min(1, Math.max(0, numeric))
}

const rawEntries = computed(() =>
  Object.entries(props.prediction ?? {})
    .map(([key, value]) => ({
      key,
      label: modelLabels[key] ?? key,
      score: clampScore(value),
    }))
    .sort((left, right) => right.score - left.score),
)

const topScore = computed(() => rawEntries.value[0]?.score ?? 0)
const hasConfidentMatch = computed(() => topScore.value >= 0.001)
const visibleEntries = computed(() => rawEntries.value.filter((entry) => entry.score >= 0.001))
const topLabel = computed(() => (hasConfidentMatch.value ? rawEntries.value[0]?.label : 'Нет уверенного следа'))
const endpointLabel = computed(() => (props.source?.includes('pangramlabs') ? 'Отдельный endpoint' : 'Атрибуция моделей'))
const localizedLabel = computed(() => localizePredictionText(props.label) || props.label)

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

.llm-prediction-card__top--muted {
  background: var(--bg-sunken);
  border-color: var(--border);
  color: var(--muted);
}

.llm-prediction-card__options {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.llm-prediction-card__options span {
  background: var(--bg-sunken);
  border-radius: 999px;
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
  padding: 4px 7px;
}

.llm-prediction-card__summary {
  align-items: center;
  background: var(--paper-hover);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--ink-2);
  display: flex;
  font-size: 11px;
  font-weight: 700;
  gap: 8px;
  justify-content: space-between;
  min-width: 0;
  padding: 8px 10px;
}

.llm-prediction-card__request {
  color: var(--muted);
  font-size: 10px;
  margin: -6px 0 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.llm-prediction-card__note {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.45;
  margin: -4px 0 0;
}

.llm-prediction-card__empty {
  background: var(--bg-sunken);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.45;
  margin: 0;
  padding: 9px 10px;
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
