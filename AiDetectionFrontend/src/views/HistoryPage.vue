<template>
  <VeritasShell active="history" :breadcrumbs="breadcrumbs">
    <section class="history-page">
      <header class="history-page__header">
        <div class="history-page__heading">
          <h1 class="serif history-page__title">История анализов</h1>
          <p class="history-page__subtitle">Все проверки, которые вы проводили.</p>
        </div>

        <div class="history-page__actions">
          <button class="va-btn" type="button" @click="exportCsv">
            <VIcon name="download" :size="14" />
            Экспорт CSV
          </button>
          <button class="va-btn primary" type="button" @click="goToNewAnalysis">
            <VIcon name="plus" :size="14" />
            Новый анализ
          </button>
        </div>
      </header>

      <section v-if="stats" class="stats-grid">
        <article class="va-card stat-card">
          <p class="stat-card__label">Всего анализов</p>
          <p class="serif tnum stat-card__value">{{ stats.total_analyses }}</p>
          <p class="stat-card__hint">за всё время</p>
        </article>

        <article class="va-card stat-card">
          <p class="stat-card__label">Средняя доля ИИ</p>
          <p class="serif tnum stat-card__value">{{ Math.round(stats.avg_ai_likelihood * 100) }}%</p>
          <p class="stat-card__hint">по всем документам</p>
        </article>

        <article class="va-card stat-card">
          <p class="stat-card__label">Сгенерировано ИИ</p>
          <p class="serif tnum stat-card__value">{{ stats.ai_generated }}</p>
          <p class="stat-card__hint">документов</p>
        </article>

        <article class="va-card stat-card">
          <p class="stat-card__label">Написано человеком</p>
          <p class="serif tnum stat-card__value">{{ stats.human_generated }}</p>
          <p class="stat-card__hint">документов</p>
        </article>
      </section>

      <section class="filters-row">
        <div class="filters-toggle">
          <button
            v-for="filter in filters"
            :key="filter.id"
            class="filters-toggle__button"
            :class="{ 'filters-toggle__button--active': activeFilter === filter.id }"
            type="button"
            @click="activeFilter = filter.id"
          >
            {{ filter.label }}
          </button>
        </div>

        <select v-model.number="pageSize" class="va-input page-size-select">
          <option :value="10">10 на странице</option>
          <option :value="25">25 на странице</option>
          <option :value="50">50 на странице</option>
        </select>

        <div class="search-box">
          <VIcon name="search" :size="14" class="search-box__icon" />
          <input v-model="searchQuery" class="va-input search-box__input" placeholder="Поиск по истории..." />
        </div>

        <span class="filters-row__spacer" />
        <span class="tnum filters-row__count">{{ filteredItems.length }} записей</span>
      </section>

      <p v-if="isLoading" class="table-state">Загрузка...</p>

      <section v-else class="va-card table-card">
        <header class="table-head">
          <span>Документ</span>
          <span>Формат</span>
          <span>Режим</span>
          <span>Слов</span>
          <span>ИИ %</span>
          <span>Вердикт</span>
          <span>Дата</span>
          <span />
        </header>

        <button
          v-for="(item, index) in filteredItems"
          :key="item.id"
          class="table-row"
          :class="{ 'table-row--last': index === filteredItems.length - 1 }"
          type="button"
          @click="goToAnalysis(item.id)"
        >
          <div class="doc-cell">
            <VIcon name="file" :size="14" class="doc-cell__icon" />
            <div class="doc-cell__content">
              <p class="doc-cell__title">{{ displayFilename(item.filename, item.file_type) }}</p>
            </div>
          </div>

          <span class="file-type-chip" :class="fileTypeClass(item.file_type)">
            {{ item.file_type || '—' }}
          </span>

          <span class="check-mode-chip" :class="checkModeClass(item.api_endpoint)">
            {{ checkModeLabel(item.api_endpoint) }}
          </span>

          <span class="tnum row-word-count">{{ item.text_length?.toLocaleString('ru') || '0' }}</span>

          <div class="ai-meter-row">
            <div class="ai-meter">
              <div class="ai-meter__fill" :style="aiFillStyle(item)" />
            </div>
            <span class="tnum ai-meter-row__value">{{ aiPercent(item) }}%</span>
          </div>

          <div class="verdict-cell">
            <VerdictBadge :verdict="verdictFromItem(item)" />
          </div>
          <span class="row-date">{{ fmtDate(item.created_at) }}</span>
          <VIcon name="chevRight" :size="14" class="row-chevron" />
        </button>

        <p v-if="filteredItems.length === 0" class="table-state">Нет записей</p>
      </section>

      <footer v-if="totalPages > 1" class="pagination">
        <button class="va-btn ghost pagination__button" type="button" :disabled="page <= 1" @click="page -= 1">
          <VIcon name="chevLeft" :size="13" />
        </button>

        <span class="tnum pagination__label">{{ page }} / {{ totalPages }}</span>

        <button
          class="va-btn ghost pagination__button"
          type="button"
          :disabled="page >= totalPages"
          @click="page += 1"
        >
          <VIcon name="chevRight" :size="13" />
        </button>
      </footer>
    </section>
  </VeritasShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import VeritasShell from '../components/VeritasShell.vue'
import VIcon from '../components/VIcon.vue'
import VerdictBadge from '../components/VerdictBadge.vue'
import { aiDetectionAPI } from '../services/api'
import type { Detection, StatsResponse } from '../types/api'
import {
  formatRuDate,
  resolveAiDistribution,
  resolveAiPercent,
  resolveVerdict,
  type Verdict,
} from '../utils/aiResult'

type FilterId = 'all' | Verdict

interface FilterOption {
  id: FilterId
  label: string
}

const router = useRouter()

const breadcrumbs = [{ label: 'История' }]
const isLoading = ref(false)
const items = ref<Detection[]>([])
const stats = ref<StatsResponse | null>(null)
const activeFilter = ref<FilterId>('all')
const searchQuery = ref('')
const page = ref(1)
const pageSize = ref(25)
const totalPages = ref(1)

const filters: FilterOption[] = [
  { id: 'all', label: 'Все' },
  { id: 'ai', label: 'ИИ' },
  { id: 'mixed', label: 'Смешанные' },
  { id: 'human', label: 'Человек' },
]

const aiSource = (item: Detection) => item.full_response ?? item
const verdictFromItem = (item: Detection): Verdict => resolveVerdict(aiSource(item))
const aiPercent = (item: Detection) => resolveAiPercent(aiSource(item))

const aiColor = (item: Detection): string => {
  const verdict = verdictFromItem(item)
  if (verdict === 'ai') return 'var(--ai)'
  if (verdict === 'human') return 'var(--human)'
  return 'var(--mixed)'
}

const aiFillStyle = (item: Detection) => ({
  '--fill-width': `${aiPercent(item)}%`,
  '--fill-color': aiColor(item),
})

const fileTypeClass = (value?: string) => {
  const normalized = (value || '').toLowerCase()
  if (normalized === 'pdf') return 'file-type-chip--pdf'
  if (normalized === 'doc' || normalized === 'docx') return 'file-type-chip--doc'
  return 'file-type-chip--txt'
}

const checkModeLabel = (apiEndpoint?: string) => {
  const value = (apiEndpoint || '').toLowerCase()
  return value === 'v3_detailed' ? 'Расширенная' : 'Быстрая'
}

const checkModeClass = (apiEndpoint?: string) => {
  const value = (apiEndpoint || '').toLowerCase()
  return value === 'v3_detailed' ? 'check-mode-chip--extended' : 'check-mode-chip--quick'
}

const displayFilename = (value?: string, fileType?: string) => {
  if ((fileType || '').toLowerCase() === 'text') return 'Ввод текста'
  if (!value) return 'Без имени'
  return value === 'direct_text_input' ? 'Ввод текста' : value
}

const fmtDate = (value: string) => formatRuDate(value)

const filteredItems = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  const byFilter =
    activeFilter.value === 'all'
      ? items.value
      : items.value.filter((item) => verdictFromItem(item) === activeFilter.value)

  if (!query) return byFilter

  return byFilter.filter((item) => {
    const fileName = displayFilename(item.filename, item.file_type).toLowerCase()
    const prediction = (item.prediction || '').toLowerCase()
    return fileName.includes(query) || prediction.includes(query)
  })
})

const loadHistory = async () => {
  isLoading.value = true
  try {
    const [historyResponse, statsResponse] = await Promise.all([
      aiDetectionAPI.getHistory(page.value, pageSize.value),
      aiDetectionAPI.getStats(),
    ])
    items.value = historyResponse.detections
    totalPages.value = historyResponse.pages
    stats.value = statsResponse
  } finally {
    isLoading.value = false
  }
}

const goToAnalysis = (id: number) => {
  router.push(`/analysis/${id}`)
}

const goToNewAnalysis = () => {
  router.push('/')
}

const exportCsv = () => {
  const headers = ['id', 'filename', 'file_type', 'text_length', 'ai_likelihood', 'prediction', 'created_at']
  const rows = filteredItems.value.map((item) => [
    item.id,
    `"${displayFilename(item.filename, item.file_type).replace(/"/g, '""')}"`,
    item.file_type || '',
    item.text_length || 0,
    resolveAiDistribution(aiSource(item)).ai,
    `"${(item.prediction || '').replace(/"/g, '""')}"`,
    item.created_at || '',
  ])

  const csv = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = `history-page-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  URL.revokeObjectURL(url)
}

watch(pageSize, () => {
  page.value = 1
})

watch([page, pageSize], () => {
  void loadHistory()
})

onMounted(() => {
  void loadHistory()
})
</script>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 24px 28px;
}

.history-page__header {
  align-items: flex-end;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: space-between;
}

.history-page__title {
  font-size: 28px;
  font-weight: 400;
  letter-spacing: -0.01em;
  line-height: 1.1;
  margin: 0;
}

.history-page__subtitle {
  color: var(--muted);
  font-size: 13px;
  margin: 4px 0 0;
}

.history-page__actions {
  display: flex;
  gap: 8px;
}

.stats-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.stat-card {
  padding: 16px;
}

.stat-card__label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  margin: 0;
  text-transform: uppercase;
}

.stat-card__value {
  font-size: 32px;
  font-weight: 400;
  line-height: 1.1;
  margin: 6px 0 0;
}

.stat-card__hint {
  color: var(--muted);
  font-size: 11px;
  margin: 2px 0 0;
}

.filters-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.filters-toggle {
  background: var(--bg-sunken);
  border-radius: 8px;
  display: inline-flex;
  padding: 3px;
}

.filters-toggle__button {
  background: transparent;
  border: none;
  border-radius: 5px;
  box-shadow: none;
  color: var(--muted);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 500;
  padding: 6px 12px;
}

.filters-toggle__button--active {
  background: var(--paper);
  box-shadow: var(--shadow-sm);
  color: var(--ink);
}

.page-size-select {
  height: 32px;
}

.search-box {
  min-width: 240px;
  position: relative;
}

.search-box__icon {
  color: var(--muted-2);
  left: 10px;
  pointer-events: none;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
}

.search-box__input {
  height: 32px;
  min-width: 240px;
  padding-left: 32px;
}

.filters-row__spacer {
  flex: 1;
}

.filters-row__count {
  color: var(--muted);
  font-size: 12px;
}

.table-card {
  overflow: hidden;
  padding: 0;
}

.table-head,
.table-row {
  align-items: center;
  column-gap: 0;
  display: grid;
  grid-template-columns: 0.85fr 90px 110px 110px 110px 170px 140px 40px;
  padding: 10px 16px;
}

.table-head {
  border-bottom: 1px solid var(--border);
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.table-row {
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  font-family: var(--font-sans);
  padding-top: 12px;
  padding-bottom: 12px;
  text-align: left;
  transition: background 0.08s ease;
  width: 100%;
}

.table-row:hover {
  background: var(--paper-hover);
}

.table-row--last {
  border-bottom: none;
}

.doc-cell {
  align-items: center;
  display: flex;
  gap: 10px;
  min-width: 0;
}

.doc-cell__icon {
  color: var(--muted);
  flex-shrink: 0;
}

.doc-cell__content {
  min-width: 0;
}

.doc-cell__title {
  font-size: 13px;
  font-weight: 500;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-type-chip {
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  padding: 2px 6px;
  text-transform: uppercase;
  width: fit-content;
}

.file-type-chip--doc {
  background: #e4eefa;
  color: #2e5a8c;
}

.file-type-chip--pdf {
  background: #fdecec;
  color: #a63b3b;
}

.file-type-chip--txt {
  background: #eeebe3;
  color: #5a5143;
}

.check-mode-chip {
  border-radius: 999px;
  display: inline-flex;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 3px 8px;
  text-transform: uppercase;
  width: fit-content;
}

.check-mode-chip--quick {
  background: #efeafc;
  color: #4f3f8a;
}

.check-mode-chip--extended {
  background: #e6f3ec;
  color: #2f6b49;
}

.row-word-count {
  font-size: 13px;
}

.ai-meter-row {
  align-items: center;
  display: flex;
  gap: 8px;
}

.ai-meter {
  background: var(--bg-sunken);
  border-radius: 2px;
  height: 4px;
  overflow: hidden;
  width: 40px;
}

.ai-meter__fill {
  background: var(--fill-color);
  height: 100%;
  width: var(--fill-width);
}

.ai-meter-row__value {
  font-size: 13px;
  font-weight: 500;
}

.row-date {
  color: var(--muted);
  font-size: 12px;
}

.verdict-cell {
  display: flex;
  justify-content: left;
}

.verdict-cell :deep(*) {
  width: fit-content;
}

.row-chevron {
  color: var(--muted-2);
}

.table-state {
  color: var(--muted);
  font-size: 13px;
  margin: 0;
  padding: 40px;
  text-align: center;
}

.pagination {
  align-items: center;
  display: flex;
  gap: 8px;
  justify-content: center;
}

.pagination__button {
  height: 32px;
}

.pagination__label {
  color: var(--muted);
  font-size: 13px;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 980px) {
  .history-page {
    padding: 16px;
  }

  .table-card {
    overflow-x: auto;
  }

  .table-head,
  .table-row {
    min-width: 760px;
  }
}

@media (max-width: 700px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .history-page__actions {
    width: 100%;
  }
}
</style>
