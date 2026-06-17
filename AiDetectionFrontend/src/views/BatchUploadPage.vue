<template>
  <VeritasShell active="batch" :breadcrumbs="[{ label: 'Пакетная проверка' }]">
    <section class="batch-page">
      <header class="batch-hero">
        <div>
          <p class="batch-kicker">Массовый анализ документов</p>
          <h1>Пакетная проверка</h1>
          <p class="batch-hero__copy">
            Загрузите до 50 файлов, запустите параллельную проверку и получите сводку по ИИ-тексту,
            подозрительным фрагментам и документам, которые требуют ручного просмотра.
          </p>
        </div>

        <div class="batch-hero__stats">
          <div>
            <span class="tnum">{{ files.length }}</span>
            <p>в очереди</p>
          </div>
          <div>
            <span class="tnum">{{ doneCount }}</span>
            <p>готово</p>
          </div>
          <div>
            <span class="tnum">{{ errorCount }}</span>
            <p>ошибок</p>
          </div>
        </div>
      </header>

      <div class="batch-layout">
        <div class="batch-main">
          <section class="va-card upload-card" @dragover.prevent @drop.prevent="onDrop">
            <div class="upload-card__icon">
              <VIcon name="upload" :size="22" />
            </div>
            <div class="upload-card__text">
              <h2>Добавьте документы для проверки</h2>
              <p>Поддерживаются DOCX, DOC, PDF и TXT. Максимум 50 файлов, до 25 МБ каждый.</p>
            </div>
            <label class="va-btn primary upload-card__button">
              Выбрать файлы
              <input type="file" accept=".docx,.pdf,.txt,.doc" multiple @change="onFilesChange" />
            </label>
          </section>

          <section class="va-card queue-card">
            <div class="queue-card__header">
              <div>
                <h2>Очередь проверки</h2>
                <p>{{ files.length ? `Документов: ${files.length}` : 'Файлы пока не добавлены' }}</p>
              </div>
              <div class="queue-card__actions">
                <button class="va-btn ghost" type="button" :disabled="files.length === 0" @click="clearAll">
                  Очистить
                </button>
                <button
                  class="va-btn accent"
                  type="button"
                  :disabled="isRunning || files.length === 0"
                  @click="runAll"
                >
                  <VIcon name="zap" :size="13" />
                  {{ isRunning ? 'Проверяем...' : 'Запустить все' }}
                </button>
              </div>
            </div>

            <div v-if="files.length === 0" class="queue-empty">
              <div class="queue-empty__icon">
                <VIcon name="file" :size="22" />
              </div>
              <h3>Очередь пуста</h3>
              <p>Перетащите документы в область выше или выберите файлы с компьютера.</p>
            </div>

            <div v-else class="queue-list">
              <article
                v-for="(item, index) in files"
                :key="`${item.file.name}-${index}`"
                class="queue-row"
                :class="{ 'queue-row--active': selectedIndex === index }"
                @click="selectFile(index)"
              >
                <div class="queue-row__file">
                  <VIcon name="file" :size="15" />
                  <div>
                    <h3 :title="item.file.name">{{ item.file.name }}</h3>
                    <p>{{ formatFileSize(item.file.size) }}</p>
                  </div>
                </div>

                <div class="queue-row__words">
                  <span v-if="item.result" class="tnum">{{ item.result.text_length?.toLocaleString('ru') || 0 }}</span>
                  <span v-else>—</span>
                  <p>слов</p>
                </div>

                <div class="queue-row__score">
                  <template v-if="item.result">
                    <div class="score-bar">
                      <span :style="{ width: `${aiPercentFromResult(item.result)}%` }" />
                    </div>
                    <strong class="tnum">{{ Math.round(aiPercentFromResult(item.result)) }}%</strong>
                  </template>
                  <template v-else-if="item.progress > 0">
                    <div class="score-bar score-bar--progress">
                      <span :style="{ width: `${item.progress}%` }" />
                    </div>
                    <strong class="tnum">{{ item.progress }}%</strong>
                  </template>
                  <span v-else class="queue-row__muted">Ожидает</span>
                </div>

                <div class="queue-row__status">
                  <span v-if="item.error" class="va-chip ai" :title="item.error">Ошибка</span>
                  <span v-else-if="item.result" :class="`va-chip ${verdictFromResult(item.result)}`">
                    {{ verdictLabelFromResult(item.result) }}
                  </span>
                  <span v-else-if="item.progress > 0" class="va-chip accent">В работе</span>
                  <span v-else class="va-chip">В очереди</span>
                </div>

                <div class="queue-row__actions">
                  <button
                    class="va-btn ghost icon-btn"
                    type="button"
                    title="Повторить проверку"
                    :disabled="item.progress > 0 && item.progress < 100"
                    @click.stop="runOne(index)"
                  >
                    <VIcon name="refresh" :size="13" />
                  </button>
                  <button
                    class="va-btn ghost icon-btn"
                    type="button"
                    title="Удалить"
                    @click.stop="removeFile(index)"
                  >
                    <VIcon name="x" :size="14" />
                  </button>
                </div>
              </article>
            </div>
          </section>
        </div>

        <aside class="batch-sidebar">
          <section v-if="selected && selected.result" class="va-card detail-card">
            <div class="detail-card__header">
              <div>
                <p>Выбранный документ</p>
                <h2 :title="selected.file.name">{{ selected.file.name }}</h2>
              </div>
              <VerdictBadge :verdict="verdictFromResult(selected.result)" />
            </div>

            <div class="detail-score">
              <span class="tnum">{{ Math.round(aiPercentFromResult(selected.result)) }}</span>
              <p>% вероятность ИИ</p>
            </div>

            <div>
              <h3 class="section-label">Подозрительные фрагменты</h3>
              <AiFragmentsList :windows="selected.result.pangram_response?.windows" :limit="20" />
            </div>

            <div class="detail-card__actions">
              <button class="va-btn ghost" type="button" @click="rerunSelected">
                <VIcon name="refresh" :size="13" />
                Повторить
              </button>
              <button class="va-btn accent" type="button" @click="openDetail(selected.result)">
                Полный разбор
                <VIcon name="external" :size="12" />
              </button>
            </div>
          </section>

          <section v-else-if="selected" class="va-card pending-card">
            <div class="pending-card__icon">
              <VIcon name="info" :size="18" />
            </div>
            <h2>Документ ещё не проверен</h2>
            <p>
              «{{ selected.file.name }}» находится в очереди. Запустите весь пакет или повторите проверку
              только для этой строки.
            </p>
          </section>

          <section class="va-card progress-card">
            <h2 class="section-label">Прогресс пакета</h2>
            <div class="progress-card__count">
              <span class="tnum">{{ doneCount }}</span>
              <p>/ {{ files.length }} готово</p>
            </div>
            <div class="progress-line">
              <span :style="{ width: files.length ? `${(doneCount / files.length) * 100}%` : '0%' }" />
            </div>
          </section>

          <section class="va-card summary-card">
            <h2 class="section-label">Сводка результатов</h2>
            <div v-for="row in summary" :key="row.label" class="summary-row">
              <span class="va-dot" :style="{ background: row.color }" />
              <p>{{ row.label }}</p>
              <strong class="tnum">{{ row.count }}</strong>
            </div>
          </section>
        </aside>
      </div>
    </section>
  </VeritasShell>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import VeritasShell from '../components/VeritasShell.vue'
import VIcon from '../components/VIcon.vue'
import VerdictBadge from '../components/VerdictBadge.vue'
import AiFragmentsList from '../components/workspace/AiFragmentsList.vue'
import { aiDetectionAPI } from '../services/api'
import type { AnalyzeResponse } from '../types/api'
import { resolveAiPercent, resolveVerdict, type Verdict } from '../utils/aiResult'

interface BatchFile {
  file: File
  progress: number
  result: AnalyzeResponse | null
  error: string
}

const router = useRouter()

const files = ref<BatchFile[]>([])
const isRunning = ref(false)
const selectedIndex = ref<number | null>(null)

const selected = computed(() => (selectedIndex.value === null ? null : files.value[selectedIndex.value] ?? null))
const doneCount = computed(() => files.value.filter((item) => item.result).length)
const errorCount = computed(() => files.value.filter((item) => item.error).length)

const summary = computed(() => {
  const done = files.value.filter((item) => item.result)
  return [
    { label: 'Человек', color: 'var(--human)', count: done.filter((item) => verdictFromResult(item.result) === 'human').length },
    { label: 'Смешанные', color: 'var(--mixed)', count: done.filter((item) => verdictFromResult(item.result) === 'mixed').length },
    { label: 'ИИ', color: 'var(--ai)', count: done.filter((item) => verdictFromResult(item.result) === 'ai').length },
  ]
})

const verdictFromResult = (result: AnalyzeResponse | null): Verdict => resolveVerdict(result?.pangram_response)
const aiPercentFromResult = (result: AnalyzeResponse | null) => resolveAiPercent(result?.pangram_response)

const verdictLabelFromResult = (result: AnalyzeResponse | null) => {
  const verdict = verdictFromResult(result)
  if (verdict === 'ai') return 'ИИ'
  if (verdict === 'human') return 'Человек'
  return 'Смешанные'
}

const formatFileSize = (size: number) => {
  if (size < 1024) return `${size} Б`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} КБ`
  return `${(size / 1024 / 1024).toFixed(1)} МБ`
}

const addFiles = (newFiles: FileList | File[]) => {
  for (const file of Array.from(newFiles)) {
    if (files.value.length < 50) {
      files.value.push({ file, progress: 0, result: null, error: '' })
    }
  }
}

const onFilesChange = (event: Event) => {
  const fileList = (event.target as HTMLInputElement).files
  if (fileList) addFiles(fileList)
}

const onDrop = (event: DragEvent) => {
  if (event.dataTransfer?.files) addFiles(event.dataTransfer.files)
}

const selectFile = (index: number) => {
  selectedIndex.value = index
}

const removeFile = (index: number) => {
  files.value.splice(index, 1)
  if (selectedIndex.value === index) {
    selectedIndex.value = null
  } else if (selectedIndex.value !== null && index < selectedIndex.value) {
    selectedIndex.value -= 1
  }
}

const clearAll = () => {
  files.value = []
  selectedIndex.value = null
}

const runOne = async (index: number) => {
  const item = files.value[index]
  if (!item) return

  item.error = ''
  item.result = null
  item.progress = 10

  try {
    item.progress = 50
    item.result = await aiDetectionAPI.uploadFile(item.file, false)
    item.progress = 100
  } catch (error) {
    const apiError = error as { error?: string } | null
    item.error = apiError?.error || 'Ошибка проверки'
    item.progress = 0
  }
}

const runAll = async () => {
  isRunning.value = true
  const pending = files.value.map((item, index) => ({ item, index })).filter(({ item }) => !item.result)
  await Promise.all(pending.map(({ index }) => runOne(index)))

  if (selectedIndex.value === null) {
    const firstDone = files.value.findIndex((item) => item.result)
    if (firstDone !== -1) selectedIndex.value = firstDone
  }

  isRunning.value = false
}

const rerunSelected = () => {
  if (selectedIndex.value !== null) runOne(selectedIndex.value)
}

const openDetail = (result: AnalyzeResponse | null) => {
  if (result?.detection_id) router.push(`/analysis/${result.detection_id}`)
}
</script>

<style scoped>
.batch-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 24px 28px 32px;
}

.batch-hero {
  align-items: end;
  display: grid;
  gap: 20px;
  grid-template-columns: minmax(0, 1fr) auto;
}

.batch-kicker,
.section-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  margin: 0 0 8px;
  text-transform: uppercase;
}

.batch-hero h1 {
  color: var(--ink);
  font-size: 34px;
  font-weight: 650;
  line-height: 1.05;
  margin: 0;
}

.batch-hero__copy {
  color: var(--muted);
  font-size: 14px;
  line-height: 1.55;
  margin: 10px 0 0;
  max-width: 760px;
}

.batch-hero__stats {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, 92px);
}

.batch-hero__stats div {
  background: var(--paper);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
}

.batch-hero__stats span {
  color: var(--ink);
  display: block;
  font-size: 24px;
  font-weight: 750;
  line-height: 1;
}

.batch-hero__stats p {
  color: var(--muted);
  font-size: 11px;
  margin: 6px 0 0;
}

.batch-layout {
  align-items: start;
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(0, 1fr) 360px;
}

.batch-main,
.batch-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.upload-card {
  align-items: center;
  display: grid;
  gap: 14px;
  grid-template-columns: 48px minmax(0, 1fr) auto;
  padding: 18px;
}

.upload-card__icon,
.pending-card__icon,
.queue-empty__icon {
  align-items: center;
  background: var(--accent-bg);
  border-radius: 12px;
  color: var(--accent-ink);
  display: flex;
  height: 44px;
  justify-content: center;
  width: 44px;
}

.upload-card__text h2,
.queue-card__header h2,
.detail-card__header h2,
.pending-card h2 {
  color: var(--ink);
  font-size: 15px;
  font-weight: 650;
  margin: 0;
}

.upload-card__text p,
.queue-card__header p,
.pending-card p {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.45;
  margin: 4px 0 0;
}

.upload-card__button {
  cursor: pointer;
  justify-content: center;
}

.upload-card__button input {
  display: none;
}

.queue-card {
  overflow: hidden;
}

.queue-card__header {
  align-items: center;
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 16px;
  justify-content: space-between;
  padding: 16px 18px;
}

.queue-card__actions,
.queue-row__actions,
.detail-card__actions {
  display: flex;
  gap: 8px;
}

.queue-empty {
  align-items: center;
  color: var(--muted);
  display: flex;
  flex-direction: column;
  padding: 44px 20px;
  text-align: center;
}

.queue-empty h3 {
  color: var(--ink);
  font-size: 15px;
  margin: 14px 0 4px;
}

.queue-empty p {
  font-size: 13px;
  line-height: 1.5;
  margin: 0;
  max-width: 320px;
}

.queue-list {
  display: flex;
  flex-direction: column;
}

.queue-row {
  align-items: center;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  display: grid;
  gap: 14px;
  grid-template-columns: minmax(180px, 1fr) 74px 120px 112px 68px;
  min-width: 0;
  padding: 13px 16px;
  transition: background 0.15s ease;
}

.queue-row:last-child {
  border-bottom: 0;
}

.queue-row:hover {
  background: var(--paper-hover);
}

.queue-row--active {
  background: var(--accent-bg);
}

.queue-row__file {
  align-items: center;
  display: flex;
  gap: 10px;
  min-width: 0;
}

.queue-row__file svg {
  color: var(--muted);
  flex: 0 0 auto;
}

.queue-row__file h3 {
  color: var(--ink);
  font-size: 13px;
  font-weight: 650;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-row__file p,
.queue-row__words p {
  color: var(--muted);
  font-size: 11px;
  margin: 2px 0 0;
}

.queue-row__words span {
  color: var(--ink);
  font-size: 13px;
  font-weight: 650;
}

.queue-row__score {
  align-items: center;
  display: flex;
  gap: 8px;
  min-width: 0;
}

.queue-row__score strong {
  color: var(--ink);
  font-size: 12px;
}

.queue-row__muted {
  color: var(--muted-2);
  font-size: 12px;
}

.score-bar,
.progress-line {
  background: var(--bg-sunken);
  border-radius: 999px;
  flex: 1;
  height: 6px;
  overflow: hidden;
}

.score-bar span,
.progress-line span {
  background: var(--ai);
  display: block;
  height: 100%;
}

.score-bar--progress span,
.progress-line span {
  background: var(--accent);
}

.icon-btn {
  height: 30px;
  justify-content: center;
  padding: 0;
  width: 30px;
}

.detail-card,
.pending-card,
.progress-card,
.summary-card {
  padding: 18px;
}

.detail-card__header {
  align-items: flex-start;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.detail-card__header p {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  margin: 0 0 5px;
  text-transform: uppercase;
}

.detail-card__header h2 {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-score {
  align-items: baseline;
  display: flex;
  gap: 8px;
  margin: 18px 0;
}

.detail-score span {
  color: var(--ink);
  font-size: 46px;
  font-weight: 750;
  line-height: 1;
}

.detail-score p {
  color: var(--muted);
  font-size: 14px;
  margin: 0;
}

.detail-card__actions {
  margin-top: 16px;
}

.detail-card__actions .va-btn {
  flex: 1;
  justify-content: center;
}

.pending-card {
  display: grid;
  gap: 12px;
}

.progress-card__count {
  align-items: baseline;
  display: flex;
  gap: 7px;
  margin-bottom: 12px;
}

.progress-card__count span {
  color: var(--ink);
  font-size: 38px;
  font-weight: 750;
  line-height: 1;
}

.progress-card__count p {
  color: var(--muted);
  font-size: 14px;
  margin: 0;
}

.summary-card {
  display: grid;
  gap: 2px;
}

.summary-row {
  align-items: center;
  border-top: 1px solid var(--border);
  display: flex;
  gap: 10px;
  padding: 10px 0;
}

.summary-row p {
  color: var(--ink-2);
  flex: 1;
  font-size: 13px;
  margin: 0;
}

.summary-row strong {
  color: var(--ink);
  font-size: 13px;
}

@media (max-width: 1180px) {
  .batch-layout {
    grid-template-columns: 1fr;
  }

  .batch-sidebar {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .detail-card,
  .pending-card {
    grid-column: 1 / -1;
  }
}

@media (max-width: 760px) {
  .batch-page {
    padding: 18px 14px 24px;
  }

  .batch-hero {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .batch-hero h1 {
    font-size: 28px;
  }

  .batch-hero__stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .upload-card {
    grid-template-columns: 44px minmax(0, 1fr);
  }

  .upload-card__button {
    grid-column: 1 / -1;
    width: 100%;
  }

  .queue-card__header {
    align-items: stretch;
    flex-direction: column;
  }

  .queue-card__actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .queue-card__actions .va-btn {
    justify-content: center;
  }

  .queue-row {
    gap: 10px;
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .queue-row__file,
  .queue-row__score {
    grid-column: 1 / -1;
  }

  .queue-row__words {
    display: none;
  }

  .queue-row__status {
    min-width: 0;
  }

  .queue-row__actions {
    justify-content: end;
  }

  .batch-sidebar {
    grid-template-columns: 1fr;
  }

  .detail-card__actions {
    flex-direction: column;
  }
}

@media (max-width: 380px) {
  .batch-page {
    padding-left: 12px;
    padding-right: 12px;
  }

  .batch-hero__stats {
    gap: 6px;
  }

  .batch-hero__stats div {
    padding: 10px 8px;
  }

  .batch-hero__stats span {
    font-size: 20px;
  }

  .queue-card__actions {
    grid-template-columns: 1fr;
  }
}
</style>
