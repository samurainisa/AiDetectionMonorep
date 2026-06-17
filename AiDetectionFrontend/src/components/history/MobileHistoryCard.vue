<template>
  <button class="mobile-history-card" type="button" @click="$emit('open', item.id)">
    <div class="mobile-history-card__top">
      <div class="mobile-history-card__file">
        <VIcon name="file" :size="15" />
        <div>
          <h3>{{ title }}</h3>
          <p>{{ fmtDate(item.created_at) }}</p>
        </div>
      </div>
      <VerdictBadge :verdict="verdict" />
    </div>

    <div class="mobile-history-card__meter">
      <div class="mobile-history-card__bar">
        <span :style="{ width: `${aiPercent}%`, background: aiColor }" />
      </div>
      <strong class="tnum">{{ aiPercent }}%</strong>
    </div>

    <div class="mobile-history-card__meta">
      <span>{{ fileType }}</span>
      <span>{{ modeLabel }}</span>
      <span class="tnum">{{ words }} слов</span>
    </div>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VIcon from '../VIcon.vue'
import VerdictBadge from '../VerdictBadge.vue'
import type { Detection } from '../../types/api'
import { displayDocumentName } from '../../utils/display'
import { formatRuDate, resolveAiPercent, resolveVerdict } from '../../utils/aiResult'

const props = defineProps<{
  item: Detection
}>()

defineEmits<{
  open: [id: number]
}>()

const source = computed(() => props.item.full_response ?? props.item)
const verdict = computed(() => resolveVerdict(source.value))
const aiPercent = computed(() => Math.round(resolveAiPercent(source.value)))
const aiColor = computed(() => {
  if (verdict.value === 'ai') return 'var(--ai)'
  if (verdict.value === 'human') return 'var(--human)'
  return 'var(--mixed)'
})

const title = computed(() => displayDocumentName(props.item.filename, props.item.file_type))

const fileType = computed(() => (props.item.file_type || 'text').toUpperCase())
const modeLabel = computed(() => ((props.item.api_endpoint || '').toLowerCase() === 'v3_detailed' ? 'Расширенная' : 'Быстрая'))
const words = computed(() => props.item.text_length?.toLocaleString('ru') || '0')
const fmtDate = (value: string) => formatRuDate(value)
</script>

<style scoped>
.mobile-history-card {
  background: var(--paper);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
  color: var(--ink);
  display: grid;
  gap: 12px;
  padding: 14px;
  text-align: left;
  width: 100%;
}

.mobile-history-card__top {
  align-items: flex-start;
  flex-wrap: wrap;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.mobile-history-card__file {
  align-items: flex-start;
  display: flex;
  gap: 9px;
  min-width: 0;
}

.mobile-history-card__file svg {
  color: var(--muted);
  flex: 0 0 auto;
  margin-top: 2px;
}

.mobile-history-card__file h3 {
  font-size: 13px;
  font-weight: 650;
  line-height: 1.25;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-history-card__file p {
  color: var(--muted);
  font-size: 11px;
  margin: 3px 0 0;
}

.mobile-history-card__meter {
  align-items: center;
  display: flex;
  gap: 10px;
}

.mobile-history-card__bar {
  background: var(--bg-sunken);
  border-radius: 999px;
  flex: 1;
  height: 7px;
  overflow: hidden;
}

.mobile-history-card__bar span {
  display: block;
  height: 100%;
}

.mobile-history-card__meter strong {
  font-size: 13px;
}

.mobile-history-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.mobile-history-card__meta span {
  background: var(--bg-sunken);
  border-radius: 999px;
  color: var(--ink-2);
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
}
</style>
