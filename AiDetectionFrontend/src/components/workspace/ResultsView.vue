<template>
  <div class="results-view">
    <section class="va-card result-card">
      <header class="section-header section-header--result">
        <div class="section-header__left">
          <span class="section-label">Результат</span>
          <VerdictBadge :verdict="verdict" />
        </div>
        <div class="section-header__right">
          <button class="va-btn ghost action-btn action-btn--sm" type="button" @click="copyResult">
            <VIcon :name="copied ? 'check' : 'copy'" :size="13" />
            {{ copied ? 'Скопировано' : 'Копировать' }}
          </button>
        </div>
      </header>

      <div class="result-card__body">
        <DonutChart :size="150" :stroke="14" :ai="aiProb" :human="humanProb" :uncertain="uncertainProb" />

        <div class="result-card__content">
          <div>
            <p class="serif result-card__title">{{ verdictText }}</p>
            <p class="result-card__subtitle">{{ verdictDescription }}</p>
          </div>

          <div class="metrics-grid">
            <MetricBar label="ИИ" :value="aiProb" color="var(--ai)" />
            <MetricBar label="Человек" :value="humanProb" color="var(--human)" />
            <MetricBar label="Неопр." :value="uncertainProb" color="var(--mixed)" />
          </div>
        </div>
      </div>
    </section>

    <section v-if="response" class="va-card model-card">
      <header class="section-header model-card__header">
        <div class="section-header__left">
          <span class="section-label">Модель проверки</span>
          <span class="va-chip mixed">
            <span class="va-dot mixed" />
            {{ analysisModeLabel }}
          </span>
        </div>
      </header>

      <div class="model-card__body">
        <div class="model-card__main">
          <p class="model-card__name">{{ modelDisplayName }}</p>
          <p class="model-card__description">{{ modelDescription }}</p>
        </div>

        <div class="model-card__facts">
          <span>Провайдер: {{ providerLabel }}</span>
          <span v-if="modelBaseLabel">База: {{ modelBaseLabel }}</span>
          <span v-if="confidenceLabel">Уверенность: {{ confidenceLabel }}</span>
          <span v-if="windowCountLabel">Окон: {{ windowCountLabel }}</span>
          <span v-if="windowTokenLabel">Окно: {{ windowTokenLabel }} токенов</span>
          <span v-if="windowOverlapLabel">Перекрытие: {{ windowOverlapLabel }} токенов</span>
          <span v-if="response?.input_truncated">Текст был обрезан до лимита</span>
        </div>

        <div v-if="metricChips.length" class="model-card__metrics">
          <span v-for="metric in metricChips" :key="metric.label" class="model-card__metric">
            {{ metric.label }} <strong>{{ metric.value }}</strong>
          </span>
        </div>
      </div>
    </section>

    <LlmPredictionCard
      :prediction="response?.llm_prediction"
      :label="response?.llm_prediction_label"
      :ai-likelihood="response?.llm_prediction_ai_likelihood"
      :source="response?.llm_prediction_source"
      :request-id="response?.llm_prediction_request_id"
    />

    <section v-if="showSegments" class="va-card segment-card">
      <header class="section-header segment-card__header">
        <div class="section-header__left">
          <span class="section-label">Посегментная разметка</span>
        </div>

        <div class="section-header__right">
          <div class="segment-mode-switch">
            <button
              v-for="mode in segModes"
              :key="mode.id"
              class="seg-mode-btn"
              :class="{ 'seg-mode-btn--active': segMode === mode.id }"
              type="button"
              @click="segMode = mode.id"
            >
              {{ mode.label }}
            </button>
          </div>

          <button class="va-btn ghost action-btn action-btn--sm" type="button" @click="$emit('goto-detail')">
            Полный разбор
            <VIcon name="external" :size="12" />
          </button>
        </div>
      </header>

      <div class="segment-card__content va-scroll">
        <div v-if="windows && windows.length" class="segment-text" :data-seg-mode="segMode">
          <span
            v-for="(windowItem, index) in windows.slice(0, 15)"
            :key="index"
            class="seg"
            :data-p="probBucket(windowItem.ai_likelihood)"
            :data-cls="segCls(windowItem)"
            :title="segmentTitle(windowItem)"
          >
            {{ windowItem.text }}
          </span>
        </div>

        <p v-else class="segment-empty">Сегментный анализ недоступен для этого типа результата.</p>
      </div>
    </section>

    <section v-if="plagiarism" class="va-card plagiarism-card">
      <header class="section-header section-header--plagiarism">
        <div class="section-header__left">
          <span class="section-label">Плагиат</span>
          <span class="va-chip mixed">
            <span class="va-dot mixed" />
            Найдены совпадения
          </span>
        </div>

        <div class="section-header__right">
          <button class="va-btn ghost action-btn action-btn--sm" type="button" @click="$emit('goto-plagiarism')">
            Подробно
            <VIcon name="chevRight" :size="12" />
          </button>
        </div>
      </header>

      <div class="plagiarism-card__body">
        <div class="plagiarism-total">
          <p class="serif tnum plagiarism-total__value">
            {{ plagiarismPct }}<span class="plagiarism-total__percent">%</span>
          </p>
          <p class="plagiarism-total__label">Совокупные совпадения</p>
        </div>

        <div class="plagiarism-sources">
          <article v-for="doc in topSimilarDocuments" :key="doc.detection_id" class="plagiarism-source">
            <div class="plagiarism-source__bar" />
            <div class="plagiarism-source__body">
              <p class="plagiarism-source__filename">{{ doc.filename }}</p>
              <p class="plagiarism-source__meta">{{ Math.round(doc.similarity_percentage) }}% схожести</p>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section v-else-if="plagiarismPending" class="va-card plagiarism-pending-card">
      <header class="section-header section-header--plagiarism">
        <div class="section-header__left">
          <span class="section-label">Антиплагиат</span>
          <span class="va-chip mixed">
            <span class="va-dot mixed" />
            Считаем в фоне
          </span>
        </div>

      </header>

      <p class="plagiarism-pending-card__text">
        Основной результат уже готов. Проверка совпадений продолжится в фоне и появится в истории анализа.
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AnalyzeResponse, WindowData } from '../../types/api'
import VIcon from '../VIcon.vue'
import VerdictBadge from '../VerdictBadge.vue'
import DonutChart from '../DonutChart.vue'
import MetricBar from '../MetricBar.vue'
import LlmPredictionCard from '../LlmPredictionCard.vue'
import {
  localizePredictionText,
  resolveAiDistribution,
  resolveVerdict,
  segmentVerdictClass,
  segmentVerdictLabel,
} from '../../utils/aiResult'

defineEmits(['goto-detail', 'goto-plagiarism'])

const props = withDefaults(
  defineProps<{ detection: AnalyzeResponse | null; detailed?: boolean }>(),
  { detailed: true },
)

const segMode = ref('highlight')
const segModes = [
  { id: 'highlight', label: 'Подсветка' },
  { id: 'underline', label: 'Подчёркивание' },
  { id: 'pills', label: 'Плашки' },
]

const response = computed(() => props.detection?.pangram_response)
const distribution = computed(() => resolveAiDistribution(response.value))
const aiProb = computed(() => distribution.value.ai)
const humanProb = computed(() => distribution.value.human)
const uncertainProb = computed(() => distribution.value.uncertain)
const windows = computed(() => response.value?.windows ?? [])
const showSegments = computed(() => props.detailed || windows.value.length > 0)
const isLocalModel = computed(() => response.value?.provider === 'local' || response.value?.analysis_mode === 'local')
const providerLabel = computed(() =>
  response.value?.provider_label || (isLocalModel.value ? 'Локальная модель' : 'Облачная проверка'),
)
const analysisModeLabel = computed(() => {
  if (response.value?.analysis_mode_label) return response.value.analysis_mode_label
  if (isLocalModel.value) return 'Обычная проверка'
  return props.detailed ? 'Расширенная проверка' : 'Быстрая проверка'
})
const modelDisplayName = computed(() => {
  if (response.value?.model_display_name) return response.value.model_display_name
  if (isLocalModel.value) return 'Локальная модель'
  return props.detailed ? 'Облачная проверка, расширенный режим' : 'Облачная проверка'
})
const modelDescription = computed(() => {
  if (response.value?.model_description) return response.value.model_description
  if (isLocalModel.value) {
    return 'Пилотная локальная модель: анализирует длинный текст окнами, показывает общий результат и вероятности по фрагментам.'
  }
  return props.detailed
    ? 'Внешний детектор с посегментной разметкой, вероятными LLM-моделями и общим скорингом.'
    : 'Внешний детектор с быстрым общим скорингом вероятности ИИ без подробной модельной атрибуции.'
})
const modelBaseLabel = computed(() => response.value?.model_base || '')
const confidenceLabel = computed(() => localizeConfidence(response.value?.confidence))
const windowCountLabel = computed(() =>
  typeof response.value?.window_count === 'number' ? response.value.window_count.toLocaleString('ru-RU') : '',
)
const windowTokenLabel = computed(() =>
  typeof response.value?.window_token_limit === 'number' ? response.value.window_token_limit.toLocaleString('ru-RU') : '',
)
const windowOverlapLabel = computed(() =>
  typeof response.value?.window_overlap_tokens === 'number'
    ? response.value.window_overlap_tokens.toLocaleString('ru-RU')
    : '',
)
const metricChips = computed(() => {
  const metrics = response.value?.local_model_metrics || {}
  const labels: Record<string, string> = {
    accuracy: 'Accuracy',
    precision: 'Precision',
    recall: 'Recall',
    f1: 'F1',
  }

  return Object.entries(labels)
    .map(([key, label]) => ({ label, value: formatMetric(metrics[key]) }))
    .filter((item) => item.value)
})

const plagiarism = computed(() => props.detection?.plagiarism_report ?? null)
const plagiarismPending = computed(() =>
  props.detection?.plagiarism_status === 'pending' || Boolean(props.detection?.plagiarism_pending),
)
const plagiarismPct = computed(() =>
  plagiarism.value ? Math.round(100 - plagiarism.value.originality_percentage) : 0,
)
const topSimilarDocuments = computed(() => plagiarism.value?.similar_documents.slice(0, 3) ?? [])

const verdict = computed(() => resolveVerdict(response.value))

const formatMetric = (value: unknown) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return ''
  if (value >= 0 && value <= 1) return `${Math.round(value * 100)}%`
  return value.toLocaleString('ru-RU', { maximumFractionDigits: 2 })
}

const localizeConfidence = (value?: string) => {
  const normalized = (value || '').toLowerCase()
  const labels: Record<string, string> = {
    high_ai: 'высокая, ИИ',
    medium_ai: 'средняя, ИИ',
    uncertain: 'неопределённо',
    medium_human: 'средняя, человек',
    high_human: 'высокая, человек',
  }
  return labels[normalized] || ''
}

const verdictText = computed(() => {
  if (isLocalModel.value) {
    if (verdict.value === 'ai') return 'Высокая вероятность ИИ-генерации'
    if (verdict.value === 'human') return 'Текст вероятно написан человеком'
    return 'Результат локальной модели неоднозначный'
  }

  if (response.value?.headline?.trim()) return localizePredictionText(response.value.headline)
  if (verdict.value === 'ai') return 'Высокая вероятность генерации ИИ'
  if (verdict.value === 'human') return 'Текст написан человеком'
  return 'Вероятно, часть текста сгенерирована ИИ'
})

const verdictDescription = computed(() => {
  if (isLocalModel.value) {
    return 'Локальная модель возвращает вероятность ИИ-генерации по тексту. Проценты в круге показывают эту вероятность, а не долю сегментов документа.'
  }

  return (
    localizePredictionText(response.value?.prediction) ||
    'Мы выделили фрагменты с высокой вероятностью ИИ, пройдитесь по тексту и оцените их вручную.'
  )
})

const copied = ref(false)
const copyResult = async () => {
  const summary = [
    `Вердикт: ${verdictText.value}`,
    `Модель: ${modelDisplayName.value} (${analysisModeLabel.value})`,
    `Вероятность ИИ: ${Math.round(aiProb.value * 100)}%`,
    `Человек: ${Math.round(humanProb.value * 100)}%`,
    `Неопределённо: ${Math.round(uncertainProb.value * 100)}%`,
  ]
  if (plagiarism.value) {
    summary.push(`Плагиат: ${plagiarismPct.value}%`)
  }
  try {
    await navigator.clipboard.writeText(summary.join('\n'))
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    // Clipboard API недоступен (нет https / разрешения) — тихо игнорируем
  }
}

const probBucket = (value?: number) => Math.min(4, Math.floor((value || 0) * 5))
const segCls = (windowItem: WindowData) => segmentVerdictClass(windowItem)
const segmentTitle = (windowItem: WindowData) =>
  `${Math.round((windowItem.ai_likelihood || 0) * 100)}% ИИ · ${segmentVerdictLabel(windowItem)}`
</script>

<style scoped>
.results-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-header {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: space-between;
}

.section-header__left,
.section-header__right {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.section-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.action-btn {
  justify-content: center;
}

.action-btn--sm {
  height: 28px;
}

.result-card {
  padding: 20px;
}

.section-header--result {
  margin-bottom: 14px;
}

.result-card__body {
  align-items: center;
  display: grid;
  gap: 20px;
  grid-template-columns: 150px 1fr;
}

.result-card__content {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.result-card__title {
  font-size: 20px;
  font-weight: 400;
  line-height: 1.2;
  margin: 0;
}

.result-card__subtitle {
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.45;
  margin: 4px 0 0;
}

.metrics-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: 1fr 1fr 1fr;
}

.model-card {
  padding: 18px;
}

.model-card__header {
  margin-bottom: 10px;
}

.model-card__body {
  display: grid;
  gap: 10px;
}

.model-card__name {
  font-size: 15px;
  font-weight: 700;
  margin: 0;
}

.model-card__description {
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.45;
  margin: 4px 0 0;
}

.model-card__facts,
.model-card__metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.model-card__facts span,
.model-card__metric {
  background: var(--bg-sunken);
  border-radius: 999px;
  color: var(--ink-2);
  font-size: 11px;
  font-weight: 600;
  padding: 5px 8px;
}

.model-card__metric strong {
  color: var(--ink);
  margin-left: 4px;
}

.segment-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.segment-card__header {
  border-bottom: 1px solid var(--border);
  padding: 14px 18px;
}

.segment-mode-switch {
  background: var(--bg-sunken);
  border-radius: 6px;
  display: inline-flex;
  padding: 2px;
}

.seg-mode-btn {
  background: transparent;
  border: none;
  border-radius: 5px;
  color: var(--muted);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 500;
  padding: 4px 10px;
}

.seg-mode-btn--active {
  background: var(--paper);
  color: var(--ink);
}

.segment-card__content {
  max-height: 360px;
  overflow: auto;
  padding: 20px 22px;
}

.segment-text {
  color: var(--ink);
  display: inline;
  font-size: 14px;
  line-height: 1.7;
}

.segment-empty {
  color: var(--muted);
  font-size: 14px;
  margin: 0;
  padding: 20px 0;
}

.plagiarism-card {
  padding: 18px;
}

.plagiarism-pending-card {
  display: grid;
  gap: 10px;
  padding: 18px;
}

.plagiarism-pending-card__text {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.45;
  margin: 0;
}

.section-header--plagiarism {
  margin-bottom: 14px;
}

.plagiarism-card__body {
  align-items: center;
  display: grid;
  gap: 24px;
  grid-template-columns: 160px 1fr;
}

.plagiarism-total {
  text-align: center;
}

.plagiarism-total__value {
  font-size: 56px;
  font-weight: 400;
  line-height: 1;
  margin: 0;
}

.plagiarism-total__percent {
  color: var(--muted);
  font-size: 28px;
}

.plagiarism-total__label {
  color: var(--muted);
  font-size: 12px;
  margin: 4px 0 0;
}

.plagiarism-sources {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.plagiarism-source {
  align-items: center;
  display: flex;
  gap: 12px;
}

.plagiarism-source__bar {
  background: var(--mixed);
  border-radius: 3px;
  height: 24px;
  width: 6px;
}

.plagiarism-source__body {
  flex: 1;
  min-width: 0;
}

.plagiarism-source__filename {
  font-size: 13px;
  font-weight: 500;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plagiarism-source__meta {
  color: var(--muted);
  font-size: 11px;
  margin: 0;
}

@media (max-width: 1024px) {
  .result-card__body {
    grid-template-columns: 1fr;
    justify-items: center;
  }

  .result-card__content {
    width: 100%;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .plagiarism-card__body {
    grid-template-columns: 1fr;
  }
}
</style>
