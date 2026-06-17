<template>
  <VeritasShell active="home" :breadcrumbs="breadcrumbs">
    <div class="home-page">
      <section class="home-page__input-panel">
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
              </div>
              <button class="va-btn ghost input-card__sample-button" type="button" @click="text = sampleText">
                Вставить пример
              </button>
            </div>
          </template>

          <template v-else>
            <div class="upload-zone" @dragover.prevent @drop.prevent="onDrop">
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

              <p class="upload-zone__hint">DOCX · PDF · TXT, до 25 МБ</p>

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
          <div class="mode-switch depth-switch">
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

          <div class="home-page__options">
            <label class="option-check">
              <input v-model="checkAI" type="checkbox" class="option-check__input" />
              Проверка ИИ-генерации
            </label>

            <label class="option-check">
              <input v-model="checkPlagiarism" type="checkbox" class="option-check__input" />
              Проверка плагиата
            </label>

            <span class="home-page__options-spacer" />

            <select v-model="lang" class="va-input lang-select">
              <option value="ru">Язык: Русский</option>
              <option value="en">Language: English</option>
              <option value="auto">Авто-определение</option>
            </select>
          </div>

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
        <AnalyzingState v-else-if="analyzing" />
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
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import VeritasShell from '../components/VeritasShell.vue'
import VIcon from '../components/VIcon.vue'
import EmptyResults from '../components/workspace/EmptyResults.vue'
import AnalyzingState from '../components/workspace/AnalyzingState.vue'
import ResultsView from '../components/workspace/ResultsView.vue'
import { aiDetectionAPI } from '../services/api'
import type { AnalyzeResponse } from '../types/api'

type ModeId = 'text' | 'file'
type DepthId = 'quick' | 'extended'

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

const router = useRouter()

const breadcrumbs = [{ label: 'Анализ текста' }]
const mode = ref<ModeId>('text')
const depth = ref<DepthId>('extended')
const text = ref('')
const uploadedFile = ref<File | null>(null)
const analyzing = ref(false)
const hasResult = ref(false)
const result = ref<AnalyzeResponse | null>(null)
const resultDetailed = ref(true)
const errorMsg = ref('')
const checkAI = ref(true)
const checkPlagiarism = ref(true)
const lang = ref('ru')

const modes: ModeOption[] = [
  { id: 'text', label: 'Ввести текст', icon: 'sparkle' },
  { id: 'file', label: 'Загрузить файл', icon: 'upload' },
]

const depthModes: DepthOption[] = [
  { id: 'quick', label: 'Быстрая', icon: 'zap', hint: 'Общий результат и процент вероятности ИИ' },
  { id: 'extended', label: 'Расширенная', icon: 'layers', hint: 'Подробный разбор с подсветкой ИИ-фрагментов' },
]

const sampleText = `Предметной областью дипломной работы является процесс выявления и развития талантов детей с использованием веб-ориентированной информационной системы в условиях развивающихся стран. В центре данной предметной области находятся дети, их способности, результаты занятий, участие в секциях, а также взаимодействие между взрослыми участниками процесса.

На практике выявление талантов требует не разовой оценки, а постоянного накопления и анализа данных. Для этого необходимо учитывать личные сведения о ребёнке, его принадлежность к одной или нескольким секциям, посещаемость занятий, оценки по итогам тренировок, общую динамику результатов и рекомендации по дальнейшему развитию.`

const wordCount = computed(() => text.value.split(/\s+/).filter(Boolean).length)

const onFileChange = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) {
    uploadedFile.value = file
  }
}

const onDrop = (event: DragEvent) => {
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  uploadedFile.value = file
  mode.value = 'file'
}

const goToBatch = () => {
  router.push('/batch')
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

  const detailed = depth.value === 'extended'

  try {
    if (mode.value === 'text') {
      result.value = await aiDetectionAPI.analyzeText(text.value, detailed)
    } else {
      result.value = await aiDetectionAPI.uploadFile(uploadedFile.value as File, detailed)
    }
    resultDetailed.value = detailed
    hasResult.value = true
  } catch (error: unknown) {
    const apiError = error as { error?: string } | null
    errorMsg.value = apiError?.error || 'Ошибка анализа'
  } finally {
    analyzing.value = false
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

.home-page__options {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.option-check {
  align-items: center;
  color: var(--ink-2);
  display: inline-flex;
  font-size: 13px;
  gap: 8px;
}

.option-check__input {
  accent-color: var(--accent);
}

.home-page__options-spacer {
  flex: 1;
}

.lang-select {
  font-size: 12px;
  height: 32px;
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
  .home-page__input-panel,
  .home-page__result-panel {
    padding-left: 16px;
    padding-right: 16px;
  }
}
</style>
