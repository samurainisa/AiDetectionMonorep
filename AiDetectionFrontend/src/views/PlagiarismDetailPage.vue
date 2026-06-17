<template>
  <VeritasShell active="plagiarism" :breadcrumbs="breadcrumbs">
    <section class="plagiarism-detail">
      <header class="detail-header">
        <div class="detail-header__main">
          <div class="detail-title-row">
            <h1 class="detail-title">{{ filename }}</h1>
            <span v-if="report" class="va-chip mixed">
              <span class="va-dot mixed" />
              {{ plagiarismPercent }}% совпадений
            </span>
          </div>
          <p v-if="report" class="detail-meta">
            {{ wordsDisplay }} слов · {{ similarDocuments.length }} похожих документов ·
            {{ fmtDate(detection?.created_at) }}
          </p>
        </div>

        <div class="detail-actions">
          <button class="va-btn" type="button" @click="downloadPDF">
            <VIcon name="download" :size="14" />
            Отчёт
          </button>
          <button class="va-btn" type="button" :disabled="isRechecking" @click="recheck">
            <span v-if="isRechecking" class="va-spinner recheck-spinner" />
            Перепроверить
          </button>
          <button class="va-btn primary" type="button" @click="goToNewAnalysis">Новая проверка</button>
        </div>
      </header>

      <div v-if="isLoading" class="state state--loading">Загрузка…</div>

      <div v-else-if="error" class="state state--error">
        <p class="state-error-card">
          <VIcon name="alert" :size="14" />
          {{ error }}
        </p>
      </div>

      <section v-else-if="report" class="detail-layout">
        <aside class="sources-panel va-scroll">
          <p class="panel-label">Похожие документы · {{ similarDocuments.length }}</p>

          <div class="sources-list">
            <button
              v-for="doc in similarDocuments"
              :key="doc.detection_id"
              class="source-card"
              type="button"
              :class="{ 'source-card--active': activeSrc === doc.detection_id }"
              @click="activeSrc = doc.detection_id"
            >
              <div class="source-top">
                <span class="source-dot" />
                <span class="source-id">ID {{ doc.detection_id }}</span>
                <span class="source-spacer" />
                <span class="tnum source-score">{{ Math.round(doc.similarity_percentage) }}%</span>
              </div>

              <p class="source-name">{{ displayFilename(doc.filename) }}</p>

              <p class="source-meta">
                <span class="tnum">{{ doc.matched_fragments }} фрагм. совпали</span>
                <span>·</span>
                <span>{{ fmtDate(doc.created_at) }}</span>
              </p>
            </button>
          </div>

          <div v-if="matches.length" class="matches-section">
            <p class="panel-label">Найденные совпадения · {{ matches.length }}</p>

            <p v-if="!visibleMatches.length" class="match-empty">
              Для выбранного источника совпадений нет.
            </p>

            <article
              v-for="(match, index) in visibleMatches"
              :key="`${match.source_detection_id || 'src'}-${index}`"
              class="va-card match-card"
            >
              <div class="match-header">
                <span class="match-title">Совпадение #{{ index + 1 }}</span>
                <span class="va-chip mixed match-score">
                  {{ Math.round(match.similarity_score * 100) }}%
                </span>
              </div>
              <p class="match-text">{{ match.matched_text }}</p>
            </article>
          </div>
        </aside>

        <article class="doc-panel va-scroll">
          <div class="doc-content">
            <div v-if="detection?.extracted_text" class="doc-text">
              {{ detection.extracted_text }}
            </div>
            <p v-else class="doc-empty">Текст документа недоступен.</p>
          </div>
        </article>
      </section>
    </section>
  </VeritasShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VeritasShell from '../components/VeritasShell.vue'
import VIcon from '../components/VIcon.vue'
import { aiDetectionAPI } from '../services/api'
import type {
  DetectionDetail,
  PlagiarismMatch,
  PlagiarismReport,
  SimilarDocument,
} from '../types/api'
import { displayDocumentName } from '../utils/display'

type Breadcrumb = { label: string; onClick?: () => void }

interface NormalizedPlagiarismMatch extends PlagiarismMatch {
  source_filename?: string
}

interface RawPlagiarismReport {
  detection_id?: number
  originality_percentage?: number
  plagiarism_level?: string
  total_similarity_score?: number
  total_fragments?: number
  matched_fragments?: number
  matches_count?: number
  matches?: unknown
  similar_documents?: unknown
}

const route = useRoute()
const router = useRouter()

const isLoading = ref(false)
const isRechecking = ref(false)
const error = ref('')
const report = ref<PlagiarismReport | null>(null)
const detection = ref<DetectionDetail | null>(null)
const activeSrc = ref<number | null>(null)

const detectionId = computed(() => Number(route.params.id))

const goToList = () => {
  router.push('/plagiarism')
}

const goToNewAnalysis = () => {
  router.push('/')
}

const displayFilename = (value?: string): string => displayDocumentName(value, undefined)

const filename = computed(
  () => displayFilename(detection.value?.filename) || `Документ #${detectionId.value || '—'}`,
)
const wordsDisplay = computed(() => detection.value?.text_length?.toLocaleString('ru') || '0')
const plagiarismPercent = computed(() =>
  report.value ? Math.max(0, Math.round(100 - report.value.originality_percentage)) : 0,
)
const similarDocuments = computed(() => report.value?.similar_documents ?? [])
const matches = computed(() => report.value?.matches ?? [])

const visibleMatches = computed(() => {
  const limit = 10
  if (!activeSrc.value) {
    return matches.value.slice(0, limit)
  }
  return matches.value.filter((match) => match.source_detection_id === activeSrc.value).slice(0, limit)
})

const breadcrumbs = computed<Breadcrumb[]>(() => [
  { label: 'Плагиат', onClick: goToList },
  { label: filename.value },
])

const toNumber = (value: unknown, fallback = 0): number => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

const fmtDate = (value?: string): string => {
  if (!value) return '—'
  return new Date(value).toLocaleString('ru-RU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const normalizeMatches = (raw: unknown): NormalizedPlagiarismMatch[] => {
  if (!Array.isArray(raw)) {
    return []
  }

  return raw
    .map((item) => {
      const source = (item ?? {}) as Record<string, unknown>
      const rawSimilarity = toNumber(source.similarity_score)
      const similarityScore = rawSimilarity > 1 ? rawSimilarity / 100 : rawSimilarity
      const matchedText = String(
        source.matched_text || source.source_text || source.target_text || '',
      ).trim()

      return {
        source_detection_id: toNumber(source.source_detection_id),
        source_fragment_pos: toNumber(source.source_fragment_pos),
        target_fragment_pos: toNumber(source.target_fragment_pos),
        similarity_score: Math.max(0, similarityScore),
        matched_text: matchedText,
        match_type: String(source.match_type || 'text_similarity'),
        source_filename: source.source_filename
          ? String(source.source_filename)
          : undefined,
      }
    })
    .filter((item) => item.matched_text.length > 0)
}

const normalizeSimilarDocuments = (
  rawDocs: unknown,
  normalizedMatches: NormalizedPlagiarismMatch[],
): SimilarDocument[] => {
  if (Array.isArray(rawDocs) && rawDocs.length) {
    return rawDocs.map((item, index) => {
      const source = (item ?? {}) as Record<string, unknown>
      const fallbackId = toNumber(source.source_detection_id, index + 1)
      const detectionIdValue = toNumber(source.detection_id, fallbackId)
      const matchedFragments = toNumber(source.matched_fragments)

      return {
        detection_id: detectionIdValue,
        filename: displayFilename(
          String(source.filename || source.source_filename || `Источник #${detectionIdValue}`),
        ),
        similarity_percentage: toNumber(source.similarity_percentage),
        matched_fragments:
          matchedFragments || normalizedMatches.filter((m) => m.source_detection_id === detectionIdValue).length,
        created_at: String(source.created_at || ''),
      }
    })
  }

  const grouped = new Map<number, SimilarDocument>()
  for (const match of normalizedMatches) {
    if (!match.source_detection_id) {
      continue
    }

    const current = grouped.get(match.source_detection_id)
    if (!current) {
      grouped.set(match.source_detection_id, {
        detection_id: match.source_detection_id,
        filename: displayFilename(match.source_filename || `Источник #${match.source_detection_id}`),
        similarity_percentage: match.similarity_score * 100,
        matched_fragments: 1,
        created_at: '',
      })
      continue
    }

    current.matched_fragments += 1
    current.similarity_percentage = Math.max(
      current.similarity_percentage,
      match.similarity_score * 100,
    )
  }

  return [...grouped.values()]
}

const normalizePlagiarismReport = (
  payload: RawPlagiarismReport,
  expectedDetectionId: number,
): PlagiarismReport => {
  const matchesList = normalizeMatches(payload.matches)
  const documents = normalizeSimilarDocuments(payload.similar_documents, matchesList)
  const originality = Math.min(100, Math.max(0, toNumber(payload.originality_percentage, 100)))
  const totalFragments = toNumber(payload.total_fragments, matchesList.length)
  const matchedFragments = toNumber(
    payload.matched_fragments,
    toNumber(payload.matches_count, matchesList.length),
  )

  return {
    detection_id: toNumber(payload.detection_id, expectedDetectionId),
    total_similarity_score: toNumber(payload.total_similarity_score),
    plagiarism_level: String(payload.plagiarism_level || 'original') as PlagiarismReport['plagiarism_level'],
    originality_percentage: originality,
    total_fragments: totalFragments,
    matched_fragments: matchedFragments,
    matches: matchesList,
    similar_documents: documents,
  }
}

const load = async () => {
  const currentDetectionId = detectionId.value
  if (!Number.isFinite(currentDetectionId) || currentDetectionId <= 0) {
    error.value = 'Некорректный идентификатор проверки.'
    return
  }

  isLoading.value = true
  error.value = ''

  try {
    const [detectionResponse, reportResponse] = await Promise.all([
      aiDetectionAPI.getDetection(currentDetectionId),
      aiDetectionAPI.getPlagiarismReport(currentDetectionId),
    ])

    detection.value = detectionResponse
    report.value = normalizePlagiarismReport(reportResponse, currentDetectionId)
    activeSrc.value = report.value.similar_documents[0]?.detection_id ?? null
  } catch (requestError: unknown) {
    const parsedError = requestError as { error?: string; message?: string } | null
    error.value = parsedError?.error || parsedError?.message || 'Ошибка загрузки страницы.'
  } finally {
    isLoading.value = false
  }
}

const recheck = async () => {
  const currentDetectionId = detectionId.value
  if (!Number.isFinite(currentDetectionId) || currentDetectionId <= 0) {
    return
  }

  isRechecking.value = true
  try {
    const recheckResponse = await aiDetectionAPI.recheckPlagiarism(currentDetectionId)
    report.value = normalizePlagiarismReport(recheckResponse, currentDetectionId)
    activeSrc.value = report.value.similar_documents[0]?.detection_id ?? null
  } finally {
    isRechecking.value = false
  }
}

const downloadPDF = async () => {
  const currentDetectionId = detectionId.value
  if (!Number.isFinite(currentDetectionId) || currentDetectionId <= 0) {
    return
  }

  try {
    const blob = await aiDetectionAPI.downloadPlagiarismPDF(currentDetectionId)
    const url = URL.createObjectURL(blob)

    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `plagiarism-${currentDetectionId}.pdf`

    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)

    URL.revokeObjectURL(url)
  } catch {
    error.value = 'Не удалось скачать PDF-отчёт.'
  }
}

watch(detectionId, (nextId, prevId) => {
  if (nextId !== prevId) {
    void load()
  }
})

onMounted(() => {
  void load()
})
</script>

<style scoped>
.plagiarism-detail {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
}

.detail-header {
  align-items: flex-start;
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 16px;
  justify-content: space-between;
  padding: 20px 28px 14px;
}

.detail-header__main {
  flex: 1;
  min-width: 0;
}

.detail-title-row {
  align-items: center;
  display: flex;
  gap: 10px;
  margin-bottom: 6px;
}

.detail-title {
  font-size: 17px;
  font-weight: 600;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-meta {
  color: var(--muted);
  font-size: 12px;
  margin: 0;
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.recheck-spinner {
  border-color: var(--border-2);
  border-top-color: var(--ink);
}

.state {
  padding: 24px 28px;
}

.state--loading {
  align-items: center;
  color: var(--muted);
  display: flex;
  flex: 1;
  justify-content: center;
}

.state-error-card {
  align-items: center;
  background: var(--ai-bg);
  border: 1px solid var(--ai-bg-hi);
  border-radius: 10px;
  color: var(--ai-ink);
  display: inline-flex;
  font-size: 13px;
  gap: 8px;
  margin: 0;
  padding: 16px;
}

.detail-layout {
  display: grid;
  flex: 1;
  grid-template-columns: 360px 1fr;
  min-height: 0;
}

.sources-panel {
  background: var(--bg);
  border-right: 1px solid var(--border);
  overflow: auto;
  padding: 14px;
}

.panel-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  margin: 0 0 10px;
  padding-inline: 4px;
  text-transform: uppercase;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-card {
  background: var(--paper);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  font-family: var(--font-sans);
  padding: 14px;
  text-align: left;
  transition: border-color 0.12s ease, box-shadow 0.12s ease;
  width: 100%;
}

.source-card--active {
  border-color: var(--mixed);
  box-shadow: 0 0 0 3px rgba(201, 145, 59, 0.15);
}

.source-top {
  align-items: center;
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
}

.source-dot {
  background: var(--mixed);
  border-radius: 2px;
  height: 8px;
  width: 8px;
}

.source-id {
  color: var(--muted);
  font-size: 12px;
}

.source-spacer {
  flex: 1;
}

.source-score {
  font-size: 14px;
  font-weight: 600;
}

.source-name {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  margin: 0 0 6px;
}

.source-meta {
  align-items: center;
  color: var(--muted);
  display: flex;
  font-size: 11px;
  gap: 10px;
  margin: 0;
}

.matches-section {
  margin-top: 16px;
}

.match-empty {
  color: var(--muted);
  font-size: 12px;
  margin: 0;
  padding: 4px;
}

.match-card {
  margin-bottom: 8px;
  padding: 12px;
}

.match-header {
  align-items: center;
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.match-title {
  color: var(--muted);
  font-size: 11px;
}

.match-score {
  font-size: 10px;
  height: 20px;
}

.match-text {
  background: var(--mixed-bg);
  border-radius: 6px;
  color: var(--ink-2);
  font-size: 12px;
  line-height: 1.5;
  margin: 0;
  padding: 8px;
  white-space: pre-wrap;
}

.doc-panel {
  background: var(--paper);
  overflow: auto;
  padding: 28px 44px;
}

.doc-content {
  font-size: 15px;
  line-height: 1.75;
  margin: 0 auto;
  max-width: 720px;
}

.doc-text {
  color: var(--ink);
  white-space: pre-wrap;
}

.doc-empty {
  color: var(--muted);
  font-size: 13px;
  margin: 0;
}

@media (max-width: 1160px) {
  .detail-layout {
    grid-template-columns: 320px 1fr;
  }
}

@media (max-width: 940px) {
  .detail-header {
    flex-direction: column;
    padding-inline: 16px;
  }

  .detail-title-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .detail-title {
    max-width: 100%;
    white-space: normal;
    word-break: break-word;
  }

  .detail-actions {
    flex-wrap: wrap;
  }

  .detail-layout {
    grid-template-columns: 1fr;
  }

  .sources-panel {
    border-bottom: 1px solid var(--border);
    border-right: none;
    max-height: 50vh;
  }

  .doc-panel {
    padding: 20px 16px 28px;
  }
}
</style>
