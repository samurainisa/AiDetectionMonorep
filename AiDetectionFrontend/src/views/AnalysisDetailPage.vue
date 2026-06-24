<template>
  <VeritasShell active="history" :breadcrumbs="breadcrumbs">
    <section class="analysis-detail">
      <header class="analysis-header">
        <div class="analysis-header__top">
          <div class="analysis-header__meta">
            <div class="analysis-header__title-row">
              <h1 class="analysis-title">{{ docTitle }}</h1>
              <VerdictBadge v-if="det" :verdict="verdict" />
            </div>

            <div v-if="det" class="analysis-submeta">
              <span>{{ fmtDate(det.created_at) }}</span>
              <span class="tnum">{{ det.text_length?.toLocaleString('ru') }} слов</span>
            </div>
          </div>
        </div>

        <nav class="analysis-tabs" aria-label="Вкладки анализа">
          <button
            v-for="item in tabs"
            :key="item.id"
            class="analysis-tab"
            :class="{ 'analysis-tab--active': tab === item.id }"
            type="button"
            @click="tab = item.id"
          >
            <VIcon :name="item.icon" :size="13" />
            {{ item.label }}
          </button>
        </nav>
      </header>

      <div v-if="isLoading" class="analysis-state">Загрузка...</div>

      <div v-else-if="!det" class="analysis-state analysis-state--empty">
        <p class="analysis-state__text">Анализ не найден</p>
        <button class="va-btn" type="button" @click="goToHistory">К истории</button>
      </div>

      <div v-else class="analysis-layout">
        <MobileAnalysisTextPanel
          :windows="windows"
          :extracted-text="det.extracted_text"
          :has-windows="hasWindows"
          :seg-mode="segMode"
          :active-index="activeSeg"
          :modes="segModes"
          @update:seg-mode="segMode = $event"
          @update:active-index="activeSeg = $event"
        />

        <article class="text-panel va-scroll">
          <div class="text-panel__body">
            <div v-if="hasWindows" class="text-content" :data-seg-mode="segMode">
              <span
                v-for="(windowItem, index) in windows"
                :key="index"
                class="seg"
                :data-p="probBucket(windowItem.ai_likelihood)"
                :data-cls="segCls(windowItem)"
                :class="{ active: activeSeg === index }"
                :title="`${segmentAiPercent(windowItem)}% ИИ`"
                :ref="(element) => setSegmentRef(element, index)"
                @click="scrollToSegment(index)"
              >
                {{ windowItem.text }}
              </span>
            </div>

            <div v-else class="text-content text-content--plain">{{ det.extracted_text }}</div>
          </div>

          <div class="text-legend-wrap">
            <div class="text-legend">
              <span class="legend-pill">
                <span class="legend-dot legend-dot--ai">A</span>
                AI
              </span>

              <span class="legend-separator" />

              <span class="legend-pill">
                <span class="legend-dot legend-dot--mixed">~</span>
                Подозр.
              </span>

              <span class="legend-separator" />

              <span class="legend-pill">
                <span class="legend-dot legend-dot--human">✓</span>
                Человек
              </span>

              <span class="legend-divider" />

              <div class="seg-mode-switch">
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
            </div>
          </div>
        </article>

        <aside class="side-panel">
          <div v-if="tab === 'overview'" class="panel-scroll va-scroll">
            <div class="va-card result-card">
              <div class="result-card__header">
                <span class="panel-caption">Результат</span>
                <VerdictBadge :verdict="verdict" />
              </div>

              <div class="result-card__body">
                <DonutChart :size="150" :stroke="14" :ai="aiProb" :human="humanProb" :uncertain="uncertainProb" />

                <div class="result-card__metrics">
                  <MetricBar label="ИИ" :value="aiProb" color="var(--ai)" />
                  <MetricBar label="Человек" :value="humanProb" color="var(--human)" />
                  <MetricBar label="Неопределённо" :value="uncertainProb" color="var(--mixed)" />
                </div>
              </div>
            </div>

            <LlmPredictionCard
              :prediction="det.full_response?.llm_prediction"
              :label="det.full_response?.llm_prediction_label"
              :ai-likelihood="det.full_response?.llm_prediction_ai_likelihood"
              :source="det.full_response?.llm_prediction_source"
              :request-id="det.full_response?.llm_prediction_request_id"
            />
          </div>

          <template v-if="tab === 'details'">
            <header class="side-toolbar">
              <div class="panel-caption">Сегменты</div>

              <div class="filter-switch">
                <button
                  v-for="filterItem in segFilters"
                  :key="filterItem.id"
                  class="filter-btn"
                  :class="{ 'filter-btn--active': segFilter === filterItem.id }"
                  type="button"
                  @click="segFilter = filterItem.id"
                >
                  {{ filterItem.label }}
                </button>
              </div>
            </header>

            <div class="panel-scroll panel-scroll--tight va-scroll">
              <div class="segment-list">
                <button
                  v-for="(windowItem, index) in filteredWindows"
                  :key="index"
                  class="segment-item"
                  :class="{ 'segment-item--active': segmentIsActive(windowItem) }"
                  :style="segmentItemStyle(windowItem)"
                  type="button"
                  @click="selectSegment(windowItem)"
                >
                  <span :class="`va-chip ${segCls(windowItem)} segment-item__chip`">
                    {{ segLabel(windowItem) }}
                  </span>

                  <span class="segment-item__text">{{ segmentPreview(windowItem.text) }}</span>

                  <span class="tnum segment-item__prob">{{ segmentAiPercent(windowItem) }}%</span>
                </button>
              </div>
            </div>
          </template>

          <div v-if="tab === 'graph'" class="panel-scroll va-scroll">
            <template v-if="det.text_features">
              <div v-if="det.full_response" class="va-card metrics-card">
                <div class="panel-caption panel-caption--normal">Модель проверки</div>

                <div class="feature-list">
                  <div class="feature-row">
                    <span class="feature-row__label">Провайдер</span>
                    <span class="feature-row__value">{{ detailProviderLabel }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Режим</span>
                    <span class="feature-row__value">{{ detailModeLabel }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Модель</span>
                    <span class="feature-row__value">{{ detailModelName }}</span>
                  </div>
                  <div v-if="det.full_response.model_base" class="feature-row">
                    <span class="feature-row__label">Базовая архитектура</span>
                    <span class="feature-row__value">{{ displayValue(det.full_response.model_base) }}</span>
                  </div>
                  <div v-if="detailConfidenceLabel" class="feature-row">
                    <span class="feature-row__label">Уверенность</span>
                    <span class="feature-row__value">{{ detailConfidenceLabel }}</span>
                  </div>
                  <div v-if="det.full_response.window_count != null" class="feature-row">
                    <span class="feature-row__label">Окон анализа</span>
                    <span class="feature-row__value">{{ displayValue(det.full_response.window_count) }}</span>
                  </div>
                  <div v-if="det.full_response.window_token_limit != null" class="feature-row">
                    <span class="feature-row__label">Токенов в окне</span>
                    <span class="feature-row__value">{{ displayValue(det.full_response.window_token_limit) }}</span>
                  </div>
                  <div v-if="det.full_response.window_overlap_tokens != null" class="feature-row">
                    <span class="feature-row__label">Перекрытие окон</span>
                    <span class="feature-row__value">{{ displayValue(det.full_response.window_overlap_tokens) }}</span>
                  </div>
                  <div v-if="det.full_response.analyzed_char_count != null" class="feature-row">
                    <span class="feature-row__label">Проанализировано символов</span>
                    <span class="feature-row__value">{{ displayValue(det.full_response.analyzed_char_count) }}</span>
                  </div>
                  <div v-if="det.full_response.input_truncated" class="feature-row">
                    <span class="feature-row__label">Лимит текста</span>
                    <span class="feature-row__value">Текст был обрезан</span>
                  </div>
                  <div v-if="det.full_response.model_description" class="feature-row feature-row--stacked">
                    <span class="feature-row__label">Описание</span>
                    <span class="feature-row__value">{{ displayValue(det.full_response.model_description) }}</span>
                  </div>
                  <div v-for="metric in detailModelMetrics" :key="metric.label" class="feature-row">
                    <span class="feature-row__label">{{ metric.label }}</span>
                    <span class="feature-row__value">{{ metric.value }}</span>
                  </div>
                </div>
              </div>

              <div v-if="det.full_response" class="va-card metrics-card">
                <div class="panel-caption panel-caption--normal">Сводка анализа</div>

                <div class="feature-list">
                  <div class="feature-row">
                    <span class="feature-row__label">Версия анализа</span>
                    <span class="feature-row__value">{{ displayValue(det.full_response.version) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">ИИ-сгенерированный текст</span>
                    <span class="feature-row__value">{{ displayPercent(det.full_response.fraction_ai) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">ИИ-ассистированный текст</span>
                    <span class="feature-row__value">{{ displayPercent(det.full_response.fraction_ai_assisted) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Человеческий текст</span>
                    <span class="feature-row__value">{{ displayPercent(det.full_response.fraction_human) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Средняя вероятность ИИ</span>
                    <span class="feature-row__value">{{ displayPercent(det.full_response.avg_ai_likelihood) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Максимальная вероятность ИИ</span>
                    <span class="feature-row__value">{{ displayPercent(det.full_response.max_ai_likelihood) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">ИИ-сегменты</span>
                    <span class="feature-row__value">{{ displayValue(det.full_response.num_ai_segments) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">ИИ-ассистированные сегменты</span>
                    <span class="feature-row__value">{{ displayValue(det.full_response.num_ai_assisted_segments) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Человеческие сегменты</span>
                    <span class="feature-row__value">{{ displayValue(det.full_response.num_human_segments) }}</span>
                  </div>
                </div>
              </div>

              <div v-if="det.full_response?.llm_prediction_ai_likelihood != null" class="va-card metrics-card">
                <div class="panel-caption panel-caption--normal">Модельная атрибуция</div>

                <div class="feature-list">
                  <div class="feature-row">
                    <span class="feature-row__label">Вердикт модельного поиска</span>
                    <span class="feature-row__value">{{ displayValue(det.full_response.llm_prediction_label) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Вероятность ИИ по модельному поиску</span>
                    <span class="feature-row__value">{{ displayPercent(det.full_response.llm_prediction_ai_likelihood) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Идентификатор запроса</span>
                    <span class="feature-row__value">{{ displayValue(det.full_response.llm_prediction_request_id) }}</span>
                  </div>
                </div>
              </div>

              <div class="va-card metrics-card">
                <div class="panel-caption panel-caption--normal">Базовая статистика</div>

                <div v-if="det.text_features.basic" class="feature-list">
                  <div class="feature-row">
                    <span class="feature-row__label">Слов</span>
                    <span class="feature-row__value">{{ displayValue(det.text_features.basic.word_count) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Предложений</span>
                    <span class="feature-row__value">{{ displayValue(det.text_features.basic.sentence_count) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Средняя длина предложения</span>
                    <span class="feature-row__value">{{ displayRounded(det.text_features.basic.avg_sentence_length) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Плотность пунктуации</span>
                    <span class="feature-row__value">{{ displayPercent(det.text_features.basic.punctuation_density) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Доля верхнего регистра</span>
                    <span class="feature-row__value">{{ displayPercent(det.text_features.basic.uppercase_ratio) }}</span>
                  </div>
                </div>
              </div>

              <div v-if="det.text_features.linguistic" class="va-card metrics-card">
                <div class="panel-caption panel-caption--normal">Лингвистика</div>

                <div class="feature-list">
                  <div class="feature-row">
                    <span class="feature-row__label">Лексическое разнообразие</span>
                    <span class="feature-row__value">{{ displayPercent(det.text_features.linguistic.type_token_ratio) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Доля уникальных слов</span>
                    <span class="feature-row__value">{{ displayPercent(det.text_features.linguistic.hapax_ratio) }}</span>
                  </div>
                </div>
              </div>

              <div v-if="det.text_features.ai_detection" class="va-card metrics-card">
                <div class="panel-caption panel-caption--normal">Метрики ИИ-детекции</div>

                <div class="feature-list">
                  <div class="feature-row">
                    <span class="feature-row__label">Burstiness</span>
                    <span class="feature-row__value">{{ displayPercent(det.text_features.ai_detection.burstiness) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Лексическая предсказуемость</span>
                    <span class="feature-row__value">{{ displayPercent(det.text_features.ai_detection.lexical_predictability) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Уникальность биграмм</span>
                    <span class="feature-row__value">{{ displayPercent(det.text_features.ai_detection.bigram_uniqueness) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Уникальность триграмм</span>
                    <span class="feature-row__value">{{ displayPercent(det.text_features.ai_detection.trigram_uniqueness) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Разнообразие MTLD</span>
                    <span class="feature-row__value">{{ displayPercent(det.text_features.ai_detection.mtld_diversity) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Смещение к первому лицу</span>
                    <span class="feature-row__value">{{ displayPercent(det.text_features.ai_detection.pronoun_bias_first_person) }}</span>
                  </div>
                </div>
              </div>

              <div v-if="det.text_features.readability" class="va-card metrics-card">
                <div class="panel-caption panel-caption--normal">Читаемость</div>

                <div class="feature-list">
                  <div class="feature-row">
                    <span class="feature-row__label">Индекс русской читаемости</span>
                    <span class="feature-row__value">{{ displayRounded(det.text_features.readability.russian_readability) }}</span>
                  </div>
                </div>
              </div>

              <div v-if="det.text_features.pangram_extended" class="va-card metrics-card">
                <div class="panel-caption panel-caption--normal">Расширенные признаки Pangram</div>

                <div class="feature-list">
                  <div class="feature-row">
                    <span class="feature-row__label">Количество ИИ-предложений</span>
                    <span class="feature-row__value">{{ displayValue(det.text_features.pangram_extended.pangram_ai_sentences_count) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Разброс окон анализа</span>
                    <span class="feature-row__value">{{ displayPercent(det.text_features.pangram_extended.pangram_window_burstiness) }}</span>
                  </div>
                  <div class="feature-row">
                    <span class="feature-row__label">Дисперсия окон анализа</span>
                    <span class="feature-row__value">{{ displayPercent(det.text_features.pangram_extended.pangram_window_variance) }}</span>
                  </div>
                </div>
              </div>
            </template>

            <p v-else class="graph-empty">Дополнительные метрики недоступны.</p>
          </div>

          <footer class="side-footer">
            <span class="tnum">{{ det.text_length?.toLocaleString('ru') }} слов</span>
            <span>{{ fmtDate(det.created_at) }}</span>
          </footer>
        </aside>
      </div>
    </section>
  </VeritasShell>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VeritasShell from '../components/VeritasShell.vue'
import VIcon from '../components/VIcon.vue'
import VerdictBadge from '../components/VerdictBadge.vue'
import DonutChart from '../components/DonutChart.vue'
import MetricBar from '../components/MetricBar.vue'
import LlmPredictionCard from '../components/LlmPredictionCard.vue'
import MobileAnalysisTextPanel from '../components/analysis/MobileAnalysisTextPanel.vue'
import { aiDetectionAPI } from '../services/api'
import type { DetectionDetail, WindowData } from '../types/api'
import { displayDocumentName } from '../utils/display'
import {
  formatRuDate,
  resolveAiDistribution,
  resolveVerdict,
  segmentVerdictClass,
  segmentVerdictColor,
  segmentVerdictLabel,
  type Verdict,
} from '../utils/aiResult'

type TabId = 'overview' | 'details' | 'graph'
type SegmentModeId = 'highlight' | 'underline' | 'pills'
type SegmentFilterId = 'all' | Verdict

const route = useRoute()
const router = useRouter()

const detectionId = computed(() => {
  const id = route.params.id
  return Array.isArray(id) ? parseInt(id[0], 10) : parseInt(id as string, 10)
})

const isLoading = ref(false)
const det = ref<DetectionDetail | null>(null)
const tab = ref<TabId>('overview')
const segMode = ref<SegmentModeId>('highlight')
const activeSeg = ref<number | null>(null)
const segmentRefs = ref<HTMLElement[]>([])
const segFilter = ref<SegmentFilterId>('all')

const tabs: Array<{ id: TabId; label: string; icon: string }> = [
  { id: 'overview', label: 'Обзор', icon: 'eye' },
  { id: 'details', label: 'Детали', icon: 'list' },
  { id: 'graph', label: 'Метрики', icon: 'sliders' },
]

const segModes: Array<{ id: SegmentModeId; label: string }> = [
  { id: 'highlight', label: 'Цвет' },
  { id: 'underline', label: 'Линия' },
  { id: 'pills', label: 'Плашки' },
]

const segFilters: Array<{ id: SegmentFilterId; label: string }> = [
  { id: 'all', label: 'Все' },
  { id: 'ai', label: 'ИИ' },
  { id: 'mixed', label: 'Смеш.' },
  { id: 'human', label: 'Человек' },
]

const goToHistory = () => {
  router.push('/history')
}

const goToHome = () => {
  router.push('/')
}

const docTitle = computed(
  () => displayDocumentName(det.value?.filename, det.value?.file_type) || `Анализ #${detectionId.value}`,
)

const breadcrumbs = computed(() => [
  { label: 'История', onClick: goToHistory },
  { label: docTitle.value },
])

const hasWindows = computed(() => Boolean(det.value?.full_response?.windows?.length))
const windows = computed<WindowData[]>(() => (det.value?.full_response?.windows as WindowData[]) ?? [])

const aiSource = computed(() => det.value?.full_response ?? det.value ?? undefined)
const isLocalModel = computed(() =>
  det.value?.api_endpoint === 'local_rubert_tiny2' ||
  det.value?.full_response?.provider === 'local' ||
  det.value?.full_response?.analysis_mode === 'local',
)
const detailProviderLabel = computed(() =>
  det.value?.full_response?.provider_label || (isLocalModel.value ? 'Локальная модель' : 'Облачная проверка'),
)
const detailModeLabel = computed(() => {
  if (det.value?.full_response?.analysis_mode_label) return det.value.full_response.analysis_mode_label
  if (isLocalModel.value) return 'Обычная проверка'
  return det.value?.api_endpoint === 'v3_detailed' ? 'Расширенная проверка' : 'Быстрая проверка'
})
const detailModelName = computed(() => {
  if (det.value?.full_response?.model_display_name) return det.value.full_response.model_display_name
  if (isLocalModel.value) return 'Локальная модель'
  return det.value?.api_endpoint === 'v3_detailed' ? 'Облачная проверка, расширенный режим' : 'Облачная проверка'
})
const detailConfidenceLabel = computed(() => localizeConfidence(det.value?.full_response?.confidence))
const detailModelMetrics = computed(() => {
  const metrics = det.value?.full_response?.local_model_metrics || {}
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
const distribution = computed(() => resolveAiDistribution(aiSource.value))
const aiProb = computed(() => distribution.value.ai)
const humanProb = computed(() => distribution.value.human)
const uncertainProb = computed(() => distribution.value.uncertain)
const verdict = computed(() => resolveVerdict(aiSource.value))

const filteredWindows = computed(() => {
  if (segFilter.value === 'all') return windows.value
  return windows.value.filter((windowItem) => segCls(windowItem) === segFilter.value)
})

const probBucket = (value?: number) => Math.min(4, Math.floor((value || 0) * 5))

const segCls = (windowItem: WindowData) => segmentVerdictClass(windowItem)
const segColor = (windowItem: WindowData) => segmentVerdictColor(windowItem)
const segLabel = (windowItem: WindowData) => segmentVerdictLabel(windowItem)

const segmentPreview = (text: string) => (text.length > 60 ? `${text.slice(0, 60)}?` : text)
const segmentAiPercent = (windowItem: WindowData) => Math.round((windowItem.ai_likelihood || 0) * 100)

const segmentIndex = (windowItem: WindowData) => windows.value.indexOf(windowItem)
const segmentIsActive = (windowItem: WindowData) => activeSeg.value === segmentIndex(windowItem)

const setSegmentRef = (element: Element | ComponentPublicInstance | null, index: number) => {
  if (element instanceof HTMLElement) {
    segmentRefs.value[index] = element
  }
}

const scrollToSegment = async (index: number) => {
  if (index < 0) return
  activeSeg.value = index
  await nextTick()
  segmentRefs.value[index]?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}

const selectSegment = (windowItem: WindowData) => {
  void scrollToSegment(segmentIndex(windowItem))
}

const segmentItemStyle = (windowItem: WindowData) => {
  const color = segColor(windowItem)
  const isActive = segmentIsActive(windowItem)

  return {
    '--segment-border': isActive ? color : 'var(--border)',
    '--segment-shadow': isActive ? `0 0 0 3px ${color}22` : 'var(--shadow-sm)',
  } as Record<string, string>
}

const displayValue = (value: number | string | null | undefined) => {
  if (value === null || value === undefined || value === '') return '?'
  return String(value)
}

const displayRounded = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value) ? String(Math.round(value)) : '?'

const displayPercent = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : '?'

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

const fmtDate = (value: string) => formatRuDate(value)

onMounted(async () => {
  if (Number.isNaN(detectionId.value)) return

  isLoading.value = true
  try {
    det.value = await aiDetectionAPI.getDetection(detectionId.value)
  } catch {
    // noop
  } finally {
    isLoading.value = false
  }
})
</script>

<style scoped>
.analysis-detail {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
}

.analysis-header {
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  padding: 20px 28px 0;
}

.analysis-header__top {
  align-items: flex-start;
  display: flex;
  gap: 20px;
  justify-content: space-between;
  padding-bottom: 14px;
}

.analysis-header__meta {
  flex: 1;
  min-width: 0;
}

.analysis-header__title-row {
  align-items: center;
  flex-wrap: wrap;
  display: flex;
  gap: 10px;
  margin-bottom: 6px;
}

.analysis-title {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
  margin: 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.analysis-submeta {
  align-items: center;
  color: var(--muted);
  display: flex;
  font-size: 12px;
  gap: 14px;
}

.analysis-header__actions {
  display: flex;
  gap: 8px;
}

.analysis-tabs {
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 4px;
}

.analysis-tab {
  align-items: center;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--muted);
  cursor: pointer;
  display: inline-flex;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  gap: 6px;
  margin-bottom: -1px;
  padding: 10px 14px;
  white-space: nowrap;
}

.analysis-tab--active {
  border-bottom-color: var(--accent);
  color: var(--accent-ink);
  font-weight: 600;
}

.analysis-state {
  align-items: center;
  color: var(--muted);
  display: flex;
  flex: 1;
  justify-content: center;
}

.analysis-state--empty {
  flex-direction: column;
  gap: 12px;
}

.analysis-state__text {
  color: var(--muted);
  font-size: 15px;
  margin: 0;
}

.analysis-layout {
  display: grid;
  flex: 1;
  grid-template-columns: minmax(0, 1fr) 430px;
  min-height: 0;
}

.text-panel {
  background: var(--paper);
  overflow: auto;
  padding: 28px 44px;
  position: relative;
}

.text-panel__body {
  margin: 0 auto;
  max-width: 720px;
}

.text-content {
  color: var(--ink);
  font-size: 15px;
  line-height: 1.7;
}

.text-content--plain {
  white-space: pre-wrap;
}

.text-legend-wrap {
  bottom: 16px;
  display: flex;
  justify-content: center;
  margin-top: 32px;
  position: sticky;
}

.text-legend {
  align-items: center;
  background: var(--paper);
  border: 1px solid var(--border);
  border-radius: 999px;
  box-shadow: var(--shadow-md);
  display: flex;
  gap: 6px;
  padding: 5px;
}

.legend-pill {
  align-items: center;
  color: var(--ink-2);
  display: inline-flex;
  font-size: 12px;
  gap: 6px;
  padding: 4px 10px;
}

.legend-dot {
  align-items: center;
  border-radius: 999px;
  color: #fff;
  display: grid;
  font-size: 10px;
  font-weight: 700;
  height: 16px;
  place-items: center;
  width: 16px;
}

.legend-dot--ai {
  background: var(--ai);
}

.legend-dot--mixed {
  background: var(--mixed);
}

.legend-dot--human {
  background: var(--human);
}

.legend-separator {
  background: var(--border);
  height: 16px;
  width: 1px;
}

.legend-divider {
  background: var(--border);
  height: 20px;
  width: 1px;
}

.seg-mode-switch {
  background: var(--bg-sunken);
  border-radius: 999px;
  display: inline-flex;
  padding: 2px;
}

.seg-mode-btn {
  background: transparent;
  border: none;
  border-radius: 999px;
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

.side-panel {
  background: var(--bg);
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-scroll {
  flex: 1;
  overflow: auto;
  padding: 16px;
}

.panel-scroll--tight {
  padding: 12px;
}

.panel-caption {
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.panel-caption--normal {
  color: var(--ink-2);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0;
  margin-bottom: 10px;
  text-transform: none;
}

.result-card {
  margin-bottom: 14px;
  padding: 24px;
}

.result-card__header {
  align-items: center;
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.result-card__body {
  align-items: center;
  display: grid;
  gap: 16px;
  grid-template-columns: 150px 1fr;
}

.result-card__metrics {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.side-toolbar {
  align-items: center;
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 10px;
  justify-content: space-between;
  padding: 14px 16px;
}

.filter-switch {
  display: flex;
  gap: 4px;
}

.filter-btn {
  background: var(--paper);
  border: 1px solid var(--border);
  border-radius: 5px;
  color: var(--ink-2);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 500;
  padding: 4px 8px;
}

.filter-btn--active {
  background: var(--ink);
  border-color: var(--ink);
  color: #fff;
}

.segment-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.segment-item {
  align-items: center;
  background: var(--paper);
  border: 1px solid var(--segment-border);
  border-radius: 10px;
  box-shadow: var(--segment-shadow);
  cursor: pointer;
  display: flex;
  font-family: var(--font-sans);
  gap: 10px;
  padding: 10px 12px;
  text-align: left;
  width: 100%;
}

.segment-item__chip {
  flex-shrink: 0;
  font-size: 11px;
  height: 22px;
  padding: 0 8px;
}

.segment-item__text {
  color: var(--ink-2);
  flex: 1;
  font-size: 12px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.segment-item__prob {
  color: var(--muted);
  flex-shrink: 0;
  font-size: 11px;
}

.metrics-card {
  margin-bottom: 12px;
  padding: 16px;
}

.metrics-card:last-child {
  margin-bottom: 0;
}

.feature-list {
  margin-top: 10px;
}

.feature-row {
  align-items: center;
  border-bottom: 1px solid var(--border);
  display: flex;
  font-size: 12px;
  gap: 14px;
  justify-content: space-between;
  padding: 5px 0;
}

.feature-row:last-child {
  border-bottom: none;
}

.feature-row__label {
  color: var(--muted);
  min-width: 0;
}

.feature-row__value {
  color: var(--ink);
  font-weight: 500;
  max-width: 58%;
  min-width: 0;
  overflow: hidden;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feature-row--stacked {
  align-items: flex-start;
  flex-direction: column;
  gap: 4px;
}

.feature-row--stacked .feature-row__value {
  max-width: none;
  text-align: left;
  white-space: normal;
}

.graph-empty {
  color: var(--muted);
  font-size: 13px;
  margin: 0;
  padding: 20px 0;
}

.side-footer {
  align-items: center;
  border-top: 1px solid var(--border);
  color: var(--muted);
  display: flex;
  font-size: 12px;
  justify-content: space-between;
  padding: 12px 16px;
}

@media (max-width: 1320px) {
  .analysis-layout {
    grid-template-columns: minmax(0, 1fr) 380px;
  }

  .text-panel {
    padding: 24px 28px;
  }
}

@media (max-width: 1024px) {
  .analysis-header {
    padding: 16px 16px 0;
  }

  .analysis-layout {
    grid-template-columns: 1fr;
  }

  .text-panel {
    padding: 20px 16px 24px;
  }

  .side-panel {
    border-left: none;
    border-top: 1px solid var(--border);
    min-height: 44vh;
  }

  .result-card__body {
    grid-template-columns: 1fr;
    justify-items: center;
  }

  .result-card__metrics {
    width: 100%;
  }
}

@media (max-width: 720px) {
  .analysis-detail {
    height: auto;
    min-height: calc(100vh - 48px);
  }

  .analysis-layout {
    display: block;
    padding-bottom: 0;
  }

  .text-panel {
    display: none;
  }

  .analysis-header__top {
    flex-direction: column;
    gap: 12px;
  }

  .analysis-header__actions {
    flex-wrap: wrap;
    width: 100%;
  }

  .text-legend {
    border-radius: 14px;
    flex-wrap: wrap;
    justify-content: center;
    max-width: 100%;
  }

  .legend-separator,
  .legend-divider {
    display: none;
  }

  .seg-mode-switch {
    width: 100%;
  }

  .seg-mode-btn {
    flex: 1;
    text-align: center;
  }
}
</style>
