<template>
  <VeritasShell active="home" :breadcrumbs="breadcrumbs">
    <div class="home-page">
      <section
        class="home-page__input-panel"
        @dragenter.prevent="onDragEnter"
        @dragleave.prevent="onDragLeave"
        @dragover.prevent
        @drop.prevent="onDrop"
      >
        <div class="home-page__heading">
          <h1 class="serif home-page__title">Анализ текста</h1>
          <p class="home-page__subtitle">Вставьте текст или загрузите файл, результат появится справа.</p>
        </div>

        <div class="mode-switch">
          <button
            v-for="item in modes"
            :key="item.id"
            class="mode-switch__button"
            :class="{ 'mode-switch__button--active': mode === item.id }"
            type="button"
            @click="mode = item.id"
          >
            <VIcon :name="item.icon" :size="14" />
            {{ item.label }}
          </button>
        </div>

        <div class="va-card input-card">
          <template v-if="mode === 'text'">
            <textarea
              v-model="text"
              class="input-card__textarea"
              placeholder="Вставьте сюда текст для проверки, минимум 300 символов для стабильного результата."
            />

            <div class="input-card__footer">
              <div class="input-card__stats">
                <span class="tnum">{{ wordCount }} слов</span>
                <span class="tnum">{{ text.length }} симв.</span>
                <span class="tnum">{{ estimatedTokens.toLocaleString('ru-RU') }} токенов</span>
              </div>
              <button class="va-btn ghost input-card__sample-button" type="button" @click="text = sampleText">
                Вставить пример
              </button>
            </div>
          </template>

          <template v-else>
            <div class="upload-zone" :class="{ 'upload-zone--dragging': isDragging }">
              <div class="upload-zone__icon-wrap">
                <VIcon name="upload" :size="22" />
              </div>

              <div class="upload-zone__content">
                <p class="upload-zone__title">Перетащите файл сюда</p>
                <p class="upload-zone__subtitle">
                  или
                  <label class="upload-zone__file-link">
                    выберите на компьютере
                    <input
                      type="file"
                      accept=".docx,.pdf,.txt,.doc"
                      class="upload-zone__file-input"
                      @change="onFileChange"
                    />
                  </label>
                </p>
              </div>

              <p class="upload-zone__hint">DOCX · PDF · TXT, до 32 МБ</p>

              <div v-if="uploadedFile" class="upload-zone__file-chip">
                <VIcon name="file" :size="13" />
                {{ uploadedFile.name }}
              </div>

              <button class="va-btn ghost upload-zone__batch-button" type="button" @click="goToBatch">
                <VIcon name="layers" :size="14" />
                Несколько файлов, пакетный режим
              </button>
            </div>
          </template>
        </div>

        <div class="home-page__controls">
          <div class="provider-switch" aria-label="Модель проверки">
            <button
              v-for="item in providerOptions"
              :key="item.id"
              class="provider-card"
              :class="{ 'provider-card--active': provider === item.id }"
              type="button"
              :title="item.hint"
              @click="selectProvider(item.id)"
            >
              <span class="provider-card__icon">
                <VIcon :name="item.icon" :size="16" />
              </span>
              <span class="provider-card__body">
                <span class="provider-card__title">{{ item.label }}</span>
                <span class="provider-card__text">{{ item.short }}</span>
              </span>
            </button>
          </div>

          <div v-if="!isLocalProvider" class="mode-switch depth-switch">
            <button
              v-for="item in depthModes"
              :key="item.id"
              class="mode-switch__button"
              :class="{ 'mode-switch__button--active': depth === item.id }"
              type="button"
              :title="item.hint"
              @click="depth = item.id"
            >
              <VIcon :name="item.icon" :size="14" />
              {{ item.label }}
            </button>
          </div>
          <div v-else class="local-mode-summary">
            <span class="local-mode-summary__icon">
              <VIcon name="shield" :size="15" />
            </span>
            <span>
              <span class="local-mode-summary__title">Обычная локальная проверка</span>
              <span class="local-mode-summary__text">Вероятность ИИ/человек без сегментов и модельной атрибуции</span>
            </span>
          </div>
          <p class="depth-switch__hint">{{ activeDepthHint }}</p>

          <div class="home-page__actions">
            <button class="va-btn accent analyze-button" type="button" :disabled="analyzing" @click="runAnalysis">
              <span v-if="analyzing" class="va-spinner" />
              <VIcon v-else name="zap" :size="14" />
              {{ analyzing ? 'Анализируем...' : 'Проанализировать текст' }}
            </button>

          </div>

          <div v-if="errorMsg" class="home-page__error">{{ errorMsg }}</div>
        </div>
      </section>

      <section class="home-page__result-panel va-scroll">
        <EmptyResults v-if="!hasResult && !analyzing" />
        <AnalyzingState
          v-else-if="analyzing"
          :title="analysisStateTitle"
          :subtitle="analysisStateSubtitle"
          :progress="analysisProgress"
          :remaining-seconds="analysisRemainingSeconds"
        />
        <ResultsView
          v-else-if="hasResult"
          :detection="result"
          :detailed="resultDetailed"
          @goto-detail="gotoDetail"
          @goto-plagiarism="gotoPlagiarism"
        />
      </section>
    </div>
  </VeritasShell>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import VeritasShell from '../components/VeritasShell.vue'
import VIcon from '../components/VIcon.vue'
import EmptyResults from '../components/workspace/EmptyResults.vue'
import AnalyzingState from '../components/workspace/AnalyzingState.vue'
import ResultsView from '../components/workspace/ResultsView.vue'
import { aiDetectionAPI } from '../services/api'
import type { AnalysisProvider, AnalyzeResponse } from '../types/api'

type ModeId = 'text' | 'file'
type DepthId = 'quick' | 'extended'
type ProviderId = AnalysisProvider

interface ModeOption {
  id: ModeId
  label: string
  icon: string
}

interface DepthOption {
  id: DepthId
  label: string
  icon: string
  hint: string
}

interface ProviderOption {
  id: ProviderId
  label: string
  short: string
  icon: string
  hint: string
}

const router = useRouter()

const breadcrumbs = [{ label: 'Анализ текста' }]
const mode = ref<ModeId>('text')
const depth = ref<DepthId>('quick')
const provider = ref<ProviderId>('pangram')
const text = ref('')
const uploadedFile = ref<File | null>(null)
const isDragging = ref(false)
const analyzing = ref(false)
const hasResult = ref(false)
const result = ref<AnalyzeResponse | null>(null)
const resultDetailed = ref(false)
const errorMsg = ref('')
const analysisStartedAt = ref(0)
const estimatedAnalysisSeconds = ref(8)
const nowMs = ref(Date.now())
let analysisTimer: ReturnType<typeof setInterval> | null = null

const modes: ModeOption[] = [
  { id: 'text', label: 'Ввести текст', icon: 'sparkle' },
  { id: 'file', label: 'Загрузить файл', icon: 'upload' },
]

const depthModes: DepthOption[] = [
  { id: 'quick', label: 'Быстрая', icon: 'zap', hint: 'Общий результат и процент вероятности ИИ' },
  {
    id: 'extended',
    label: 'Расширенная',
    icon: 'layers',
    hint: 'Подробный разбор, подсветка фрагментов и вероятные модели. Работает дольше, потому что выполняется дополнительная проверка.',
  },
]

const providerOptions: ProviderOption[] = [
  {
    id: 'pangram',
    label: 'Облачная проверка',
    short: 'Быстрая или расширенная проверка',
    icon: 'zap',
    hint: 'Внешний детектор: быстрый общий скоринг или расширенный разбор с сегментами и вероятными моделями.',
  },
  {
    id: 'local',
    label: 'Локальная модель',
    short: 'Обычная проверка на вашем сервере',
    icon: 'shield',
    hint: 'Пилотная локальная модель: вероятность ИИ/человек без сегментной разметки.',
  },
]

const sampleText = `Предметной областью дипломной работы является процесс выявления и развития талантов детей с использованием веб-ориентированной информационной системы в условиях развивающихся стран. В центре данной предметной области находятся дети, их способности, результаты занятий, участие в секциях, а также взаимодействие между взрослыми участниками процесса.

На практике выявление талантов требует не разовой оценки, а постоянного накопления и анализа данных. Для этого необходимо учитывать личные сведения о ребёнке, его принадлежность к одной или нескольким секциям, посещаемость занятий, оценки по итогам тренировок, общую динамику результатов и рекомендации по дальнейшему развитию.`

const wordCount = computed(() => text.value.split(/\s+/).filter(Boolean).length)
const estimatedTokens = computed(() => Math.max(0, Math.ceil(text.value.trim().length / 4)))
const selectedSizeLabel = computed(() => {
  if (mode.value === 'text') return `${estimatedTokens.value.toLocaleString('ru-RU')} токенов`
  if (!uploadedFile.value) return 'Файл не выбран'
  return `${formatFileSize(uploadedFile.value.size)}`
})
const selectedProvider = computed(() => providerOptions.find((item) => item.id === provider.value) ?? providerOptions[0])
const isLocalProvider = computed(() => provider.value === 'local')
const analysisElapsedSeconds = computed(() =>
  analysisStartedAt.value ? Math.floor((nowMs.value - analysisStartedAt.value) / 1000) : 0,
)
const analysisRemainingSeconds = computed(() =>
  Math.max(0, estimatedAnalysisSeconds.value - analysisElapsedSeconds.value),
)
const analysisProgress = computed(() => {
  if (!analyzing.value) return 0
  const elapsed = analysisElapsedSeconds.value
  const estimate = Math.max(1, estimatedAnalysisSeconds.value)
  if (elapsed >= estimate) return 94
  return Math.max(8, Math.min(92, Math.round((elapsed / estimate) * 100)))
})
const analysisStateTitle = computed(() => (mode.value === 'file' ? 'Анализируем файл...' : 'Анализируем текст...'))
const analysisStateSubtitle = computed(() => {
  const modeText = isLocalProvider.value
    ? 'локальная обычная проверка'
    : depth.value === 'extended'
      ? 'расширенная проверка с сегментами и моделями'
      : 'быстрая проверка'
  return `${selectedSizeLabel.value} · ${selectedProvider.value.label} · ${modeText}`
})
const activeDepthHint = computed(() =>
  isLocalProvider.value
    ? 'Локальная модель работает на вашем сервере и возвращает вероятность ИИ/человек. Сегменты и вероятные LLM-модели доступны только в расширенном облачном режиме.'
    : depth.value === 'extended'
    ? 'Расширенная проверка добавит вероятные модели и подробные сегменты, поэтому займёт больше времени.'
    : 'Быстрая проверка делает один запрос и показывает общий результат без модельной атрибуции.',
)

const onFileChange = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) {
    uploadedFile.value = file
  }
}

const onDrop = (event: DragEvent) => {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  uploadedFile.value = file
  mode.value = 'file'
}
const onDragEnter = () => {
  isDragging.value = true
}
const onDragLeave = (event: DragEvent) => {
  const next = event.relatedTarget as Node | null
  if (!next || !(event.currentTarget as HTMLElement).contains(next)) isDragging.value = false
}
const goToBatch = () => {
  router.push('/batch')
}

const selectProvider = (nextProvider: ProviderId) => {
  provider.value = nextProvider
  if (nextProvider === 'local') {
    depth.value = 'quick'
  }
}

const formatFileSize = (bytes: number): string => {
  if (!bytes) return '0 Б'
  const units = ['Б', 'КБ', 'МБ', 'ГБ']
  let value = bytes
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toLocaleString('ru-RU', { maximumFractionDigits: unitIndex ? 1 : 0 })} ${units[unitIndex]}`
}

const estimateAnalysisSeconds = () => {
  const detailedMultiplier = !isLocalProvider.value && depth.value === 'extended' ? 1.65 : 1
  const textSize = mode.value === 'text' ? text.value.length : Math.round((uploadedFile.value?.size || 0) / 8)
  const base = mode.value === 'file' ? 10 : 6
  const bySize = Math.ceil(textSize / 4500)
  const byFile = mode.value === 'file' ? Math.ceil((uploadedFile.value?.size || 0) / (1024 * 1024)) : 0
  return Math.max(5, Math.min(180, Math.ceil((base + bySize + byFile) * detailedMultiplier)))
}

const startAnalysisTimer = () => {
  estimatedAnalysisSeconds.value = estimateAnalysisSeconds()
  analysisStartedAt.value = Date.now()
  nowMs.value = Date.now()
  if (analysisTimer) clearInterval(analysisTimer)
  analysisTimer = setInterval(() => {
    nowMs.value = Date.now()
  }, 250)
}

const stopAnalysisTimer = () => {
  if (analysisTimer) {
    clearInterval(analysisTimer)
    analysisTimer = null
  }
}

const runAnalysis = async () => {
  errorMsg.value = ''

  if (mode.value === 'text' && !text.value.trim()) {
    errorMsg.value = 'Введите текст для анализа'
    return
  }

  if (mode.value === 'file' && !uploadedFile.value) {
    errorMsg.value = 'Выберите файл'
    return
  }

  analyzing.value = true
  hasResult.value = false
  startAnalysisTimer()

  const detailed = provider.value === 'pangram' && depth.value === 'extended'

  try {
    if (mode.value === 'text') {
      result.value = await aiDetectionAPI.analyzeText(text.value, detailed, provider.value)
    } else {
      result.value = await aiDetectionAPI.uploadFile(uploadedFile.value as File, detailed, provider.value)
    }
    resultDetailed.value = detailed || provider.value === 'local'
    hasResult.value = true
  } catch (error: unknown) {
    const apiError = error as { error?: string } | null
    errorMsg.value = apiError?.error || 'Ошибка анализа'
  } finally {
    analyzing.value = false
    stopAnalysisTimer()
  }
}

const gotoDetail = () => {
  if (!result.value?.detection_id) return
  router.push(`/analysis/${result.value.detection_id}`)
}

const gotoPlagiarism = () => {
  if (!result.value?.detection_id) return
  router.push(`/plagiarism/${result.value.detection_id}`)
}

onUnmounted(stopAnalysisTimer)
</script>

<style scoped>
.home-page {
  display: grid;
  grid-template-columns: minmax(480px, 1fr) minmax(520px, 1.1fr);
  height: calc(100vh - 56px);
  overflow: hidden;
}

.home-page__input-panel {
  background: var(--bg);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 24px 24px 0;
}

.home-page__heading {
  margin-bottom: 18px;
}

.home-page__title {
  font-size: 28px;
  font-weight: 400;
  letter-spacing: -0.01em;
  line-height: 1.1;
  margin: 0;
}

.home-page__subtitle {
  color: var(--muted);
  font-size: 13px;
  margin: 4px 0 0;
}

.mode-switch {
  align-self: flex-start;
  background: var(--bg-sunken);
  border-radius: 10px;
  display: inline-flex;
  margin-bottom: 14px;
  padding: 3px;
}

.mode-switch__button {
  align-items: center;
  background: transparent;
  border: none;
  border-radius: 7px;
  box-shadow: none;
  color: var(--muted);
  cursor: pointer;
  display: flex;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  gap: 8px;
  padding: 7px 14px;
}

.mode-switch__button--active {
  background: var(--paper);
  box-shadow: var(--shadow-sm);
  color: var(--ink);
}

.mode-switch__button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.provider-switch {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.provider-card {
  align-items: flex-start;
  background: var(--paper);
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--ink);
  cursor: pointer;
  display: flex;
  gap: 10px;
  min-width: 0;
  padding: 12px;
  text-align: left;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

.provider-card:hover {
  border-color: rgba(237, 112, 58, 0.45);
  box-shadow: var(--shadow-sm);
}

.provider-card--active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(237, 112, 58, 0.14);
}

.provider-card__icon {
  align-items: center;
  background: var(--accent-bg);
  border-radius: 8px;
  color: var(--accent-ink);
  display: inline-flex;
  flex: 0 0 auto;
  height: 30px;
  justify-content: center;
  width: 30px;
}

.provider-card__body {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.provider-card__title {
  font-size: 13px;
  font-weight: 700;
  line-height: 1.2;
}

.provider-card__text {
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.25;
}

.local-mode-summary {
  align-items: center;
  background: var(--bg-sunken);
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--ink);
  display: flex;
  gap: 10px;
  padding: 10px 12px;
}

.local-mode-summary__icon {
  align-items: center;
  background: var(--paper);
  border-radius: 8px;
  color: var(--accent-ink);
  display: inline-flex;
  flex: 0 0 auto;
  height: 28px;
  justify-content: center;
  width: 28px;
}

.local-mode-summary__title,
.local-mode-summary__text {
  display: block;
}

.local-mode-summary__title {
  font-size: 13px;
  font-weight: 700;
  line-height: 1.2;
}

.local-mode-summary__text {
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.3;
  margin-top: 2px;
}

.input-card {
  display: flex;
  flex: 1;
  flex-direction: column;
  margin-bottom: 16px;
  min-height: 0;
  overflow: hidden;
}

.input-card__textarea {
  background: transparent;
  border: none;
  color: var(--ink);
  flex: 1;
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.6;
  outline: none;
  padding: 20px;
  resize: none;
}

.input-card__footer {
  align-items: center;
  margin-top: 20px;
  border-top: 1px solid var(--border);
  color: var(--muted);
  display: flex;
  font-size: 12px;
  justify-content: space-between;
  padding: 10px 16px;
}

.input-card__stats {
  display: flex;
  gap: 16px;
}

.input-card__sample-button {
  height: 28px;
}

.upload-zone {
  align-items: center;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  justify-content: center;
  padding: 40px;
  text-align: center;
}

.upload-zone--dragging { background: var(--accent-bg); outline: 2px dashed var(--accent); outline-offset: -8px; }

.upload-zone__icon-wrap {
  align-items: center;
  background: var(--bg-sunken);
  border-radius: 14px;
  color: var(--muted);
  display: flex;
  height: 56px;
  justify-content: center;
  width: 56px;
}

.upload-zone__title {
  font-size: 15px;
  font-weight: 500;
  margin: 0;
}

.upload-zone__subtitle {
  color: var(--muted);
  font-size: 13px;
  margin: 2px 0 0;
}

.upload-zone__file-link {
  color: var(--accent-ink);
  cursor: pointer;
  text-decoration: underline;
}

.upload-zone__file-input {
  display: none;
}

.upload-zone__hint {
  color: var(--muted-2);
  font-size: 12px;
  margin: 0;
}

.upload-zone__file-chip {
  align-items: center;
  background: var(--bg-sunken);
  border-radius: 8px;
  color: var(--ink-2);
  display: inline-flex;
  font-size: 13px;
  gap: 8px;
  margin-top: 8px;
  padding: 8px 14px;
}

.upload-zone__batch-button {
  margin-top: 8px;
}

.home-page__controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 24px;
}

.depth-switch {
  margin-bottom: 2px;
}

.depth-switch__hint {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.35;
  margin: -4px 0 0;
}

.home-page__actions {
  display: flex;
  gap: 8px;
}

.analyze-button {
  flex: 1;
  font-size: 14px;
  height: 44px;
  justify-content: center;
}

.settings-button {
  height: 44px;
  padding: 0 14px;
}

.home-page__error {
  background: var(--ai-bg);
  border-radius: 8px;
  color: var(--ai-ink);
  font-size: 13px;
  padding: 8px 12px;
}

.home-page__result-panel {
  background: var(--bg);
  overflow: auto;
  padding: 24px 24px 48px;
}

@media (max-width: 1280px) {
  .home-page {
    grid-template-columns: 1fr;
    height: auto;
    min-height: calc(100vh - 56px);
  }

  .home-page__input-panel {
    border-right: none;
    border-bottom: 1px solid var(--border);
    min-height: 60vh;
  }

  .home-page__result-panel {
    min-height: 40vh;
  }
}

@media (max-width: 768px) {
  .home-page {
    min-height: auto;
  }

  .home-page__input-panel {
    min-height: auto;
    padding-top: 18px;
  }

  .home-page__input-panel,
  .home-page__result-panel {
    padding-left: 16px;
    padding-right: 16px;
  }

  .home-page__heading {
    margin-left: auto;
    margin-right: auto;
    max-width: 340px;
    text-align: center;
  }

  .home-page__title {
    font-size: 27px;
  }

  .mode-switch {
    align-self: stretch;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
  }

  .mode-switch__button {
    justify-content: center;
    min-width: 0;
    padding-left: 8px;
    padding-right: 8px;
  }

  .provider-switch {
    grid-template-columns: 1fr;
  }

  .depth-switch {
    width: 100%;
  }

  .home-page__result-panel {
    min-height: 0;
    padding-bottom: 18px;
    padding-top: 0;
  }
}

@media (max-width: 380px) {
  .home-page__input-panel,
  .home-page__result-panel {
    padding-left: 12px;
    padding-right: 12px;
  }

  .mode-switch__button {
    font-size: 12px;
    gap: 6px;
  }
}
</style>
