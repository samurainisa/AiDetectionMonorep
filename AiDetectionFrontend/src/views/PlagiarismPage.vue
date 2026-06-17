<template>
  <VeritasShell active="plagiarism" :breadcrumbs="breadcrumbs">
    <section class="plagiarism-page">
      <header class="page-header">
        <div class="page-title-wrap">
          <h1 class="serif page-title">Плагиат</h1>
          <p class="page-subtitle">
            Поиск совпадений в базе источников: веб, научные публикации, архив работ.
          </p>
        </div>
        <button class="va-btn primary" type="button" @click="goToNewAnalysis">
          <VIcon name="plus" :size="14" />
          Новая проверка
        </button>
      </header>

      <section v-if="stats" class="stats-grid">
        <article class="va-card stat-card">
          <p class="stat-label">Всего проверок</p>
          <p class="serif tnum stat-value">{{ stats.total_analyses }}</p>
        </article>
        <article class="va-card stat-card">
          <p class="stat-label">С совпадениями</p>
          <p class="serif tnum stat-value stat-value--mixed">{{ withMatches }}</p>
        </article>
        <article class="va-card stat-card">
          <p class="stat-label">Средняя оригинальность</p>
          <p class="serif tnum stat-value stat-value--human">{{ avgOriginalityDisplay }}</p>
        </article>
      </section>

      <p v-if="isLoading" class="table-state">Загрузка…</p>
      <p v-else-if="loadError" class="table-state table-state--error">{{ loadError }}</p>

      <section v-else class="va-card table-card">
        <header class="table-head">
          <span>Документ</span>
          <span>Плагиат</span>
          <span>Слов</span>
          <span>Дата</span>
          <span />
        </header>

        <button
          v-for="(item, index) in items"
          :key="item.id"
          class="table-row"
          type="button"
          :class="{ 'table-row--last': index === items.length - 1 }"
          @click="goToDetail(item.id)"
        >
          <div class="doc-cell">
            <VIcon name="file" :size="14" class="doc-icon" />
            <span class="doc-title">{{ displayFilename(item.filename, item.file_type) }}</span>
          </div>

          <div class="plag-cell">
            <template v-if="hasOriginality(item)">
              <div class="plag-meter">
                <div
                  class="plag-meter__fill"
                  :style="{
                    width: `${plagiarismPercent(item.plagiarism_originality)}%`,
                    backgroundColor: plagColor(item.plagiarism_originality),
                  }"
                />
              </div>
              <span class="tnum row-value">
                {{ plagiarismPercent(item.plagiarism_originality) }}%
              </span>
            </template>
            <span v-else class="row-empty">—</span>
          </div>

          <span class="tnum row-value">{{ item.text_length?.toLocaleString('ru') || '—' }}</span>
          <span class="row-date">{{ fmtDate(item.created_at) }}</span>
          <VIcon name="chevRight" :size="14" class="row-chevron" />
        </button>

        <p v-if="items.length === 0" class="table-state">Нет данных</p>
      </section>

      <section v-if="!isLoading && !loadError" class="mobile-plagiarism-list" aria-label="Документы">
        <MobilePlagiarismCard
          v-for="item in items"
          :key="item.id"
          :item="item"
          @open="goToDetail"
        />
        <p v-if="items.length === 0" class="table-state">Нет данных</p>
      </section>
    </section>
  </VeritasShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import VeritasShell from '../components/VeritasShell.vue'
import VIcon from '../components/VIcon.vue'
import MobilePlagiarismCard from '../components/plagiarism/MobilePlagiarismCard.vue'
import { aiDetectionAPI } from '../services/api'
import type { Detection, StatsResponse } from '../types/api'
import { displayDocumentName } from '../utils/display'

const router = useRouter()

const breadcrumbs = [{ label: 'Плагиат' }]
const isLoading = ref(false)
const loadError = ref('')
const items = ref<Detection[]>([])
const stats = ref<StatsResponse | null>(null)

const withMatches = computed(
  () =>
    items.value.filter(
      (item) => item.plagiarism_originality != null && item.plagiarism_originality < 85,
    ).length,
)

const avgOriginalityDisplay = computed(() => {
  const originals = items.value
    .map((item) => item.plagiarism_originality)
    .filter((value): value is number => value != null)

  if (!originals.length) {
    return '—'
  }

  const average = originals.reduce((sum, value) => sum + value, 0) / originals.length
  return `${Math.round(average)}%`
})

const hasOriginality = (item: Detection): boolean => item.plagiarism_originality != null

const displayFilename = (value?: string, fileType?: string): string => displayDocumentName(value, fileType)

const plagiarismPercent = (originality: number | undefined): number => {
  const normalizedOriginality = originality ?? 100
  return Math.round(100 - normalizedOriginality)
}

const plagColor = (originality: number | undefined): string => {
  const plagiarism = plagiarismPercent(originality)
  if (plagiarism > 25) return 'var(--ai)'
  if (plagiarism > 10) return 'var(--mixed)'
  return 'var(--human)'
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

const goToDetail = (id: number) => {
  router.push(`/plagiarism/${id}`)
}

const goToNewAnalysis = () => {
  router.push('/')
}

const loadPage = async () => {
  isLoading.value = true
  loadError.value = ''

  try {
    const [history, summary] = await Promise.all([aiDetectionAPI.getHistory(1, 50), aiDetectionAPI.getStats()])
    items.value = history.detections
    stats.value = summary
  } catch {
    loadError.value = 'Не удалось загрузить страницу плагиата.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadPage)
</script>

<style scoped>
.plagiarism-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 100%;
  padding: 24px 28px;
}

.page-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.page-title-wrap {
  min-width: 0;
}

.page-title {
  font-size: 28px;
  font-weight: 400;
  letter-spacing: -0.01em;
  line-height: 1.1;
}

.page-subtitle {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.stat-card {
  padding: 18px;
}

.stat-label {
  margin: 0;
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.stat-value {
  margin: 6px 0 0;
  color: var(--ink);
  font-size: 36px;
  font-weight: 400;
  line-height: 1.1;
}

.stat-value--mixed {
  color: var(--mixed-ink);
}

.stat-value--human {
  color: var(--human-ink);
}

.table-card {
  overflow: hidden;
  padding: 0;
}

.mobile-plagiarism-list {
  display: none;
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
  width: 100%;
}

.table-head,
.table-row {
  display: grid;
  align-items: center;
  column-gap: 0;
  grid-template-columns: minmax(0, 1.4fr) 140px 100px 140px 40px;
  padding-inline: 16px;
}

.table-head {
  border-bottom: 1px solid var(--border);
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  min-height: 40px;
  text-transform: uppercase;
}

.table-row {
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  min-height: 58px;
  text-align: left;
  transition: background 0.12s ease;
  width: 100%;
}

.table-row:hover {
  background: var(--paper-hover);
}

.table-row--last {
  border-bottom: 0;
}

.doc-cell {
  align-items: center;
  display: flex;
  gap: 10px;
  min-width: 0;
}

.doc-icon {
  color: var(--muted);
  flex-shrink: 0;
}

.doc-title {
  display: block;
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plag-cell {
  align-items: center;
  display: flex;
  gap: 8px;
}

.plag-meter {
  background: var(--bg-sunken);
  border-radius: 2px;
  height: 4px;
  overflow: hidden;
  width: 60px;
}

.plag-meter__fill {
  border-radius: 2px;
  height: 100%;
}

.row-value {
  color: var(--ink);
  font-size: 13px;
  font-weight: 500;
}

.row-date {
  color: var(--muted);
  font-size: 12px;
}

.row-empty {
  color: var(--muted-2);
  font-size: 12px;
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

.table-state--error {
  color: var(--ai-ink);
}

@media (max-width: 1120px) {
  .table-head,
  .table-row {
    grid-template-columns: minmax(0, 1.3fr) 120px 90px 130px 30px;
  }
}

@media (max-width: 900px) {
  .plagiarism-page {
    padding-inline: 16px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .table-card {
    overflow-x: auto;
  }

  .table-head,
  .table-row {
    min-width: 640px;
  }
}

@media (max-width: 700px) {
  .plagiarism-page {
    padding: 14px;
  }

  .page-header .va-btn {
    justify-content: center;
    width: 100%;
  }

  .table-card {
    display: none;
  }

  .mobile-plagiarism-list {
    display: grid;
    gap: 10px;
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
