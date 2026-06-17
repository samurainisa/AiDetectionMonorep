<template>
  <button class="mobile-plagiarism-card" type="button" :disabled="!isReady" @click="openIfReady">
    <div class="mobile-plagiarism-card__top">
      <div class="mobile-plagiarism-card__file">
        <VIcon name="file" :size="15" />
        <div>
          <h3>{{ title }}</h3>
          <p>{{ date }}</p>
        </div>
      </div>
      <span v-if="isReady" class="mobile-plagiarism-card__score tnum" :style="{ color }">{{ plagiarism }}%</span>
      <span v-else class="mobile-plagiarism-card__status" :class="statusClass">{{ statusLabel }}</span>
    </div>

    <div v-if="isReady" class="mobile-plagiarism-card__meter">
      <span :style="{ width: `${plagiarism}%`, backgroundColor: color }" />
    </div>

    <div class="mobile-plagiarism-card__meta">
      <span class="tnum">{{ words }} слов</span>
      <span>{{ plagiarismLabel }}</span>
    </div>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VIcon from '../VIcon.vue'
import type { Detection } from '../../types/api'
import { displayDocumentName } from '../../utils/display'

const props = defineProps<{
  item: Detection
}>()

const emit = defineEmits<{
  open: [id: number]
}>()

const title = computed(() => displayDocumentName(props.item.filename, props.item.file_type))
const originality = computed(() => props.item.plagiarism_originality ?? 100)
const plagiarism = computed(() => Math.round(100 - originality.value))
const status = computed(() => {
  if (props.item.plagiarism_originality != null) return 'ready'
  return props.item.plagiarism_status || (props.item.plagiarism_pending ? 'pending' : 'unknown')
})
const isReady = computed(() => status.value === 'ready')
const words = computed(() => props.item.text_length?.toLocaleString('ru') || '0')
const date = computed(() =>
  props.item.created_at
    ? new Date(props.item.created_at).toLocaleString('ru-RU', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Дата неизвестна',
)

const color = computed(() => {
  if (plagiarism.value > 25) return 'var(--ai)'
  if (plagiarism.value > 10) return 'var(--mixed)'
  return 'var(--human)'
})

const plagiarismLabel = computed(() => {
  if (status.value === 'pending') return 'Проверка совпадений идет'
  if (status.value === 'unavailable') return 'Антиплагиат недоступен'
  if (status.value !== 'ready') return 'Статус пока неизвестен'
  if (plagiarism.value > 25) return 'Высокие совпадения'
  if (plagiarism.value > 10) return 'Есть совпадения'
  return 'Оригинальный текст'
})

const statusLabel = computed(() => {
  if (status.value === 'pending') return 'На подсчете'
  if (status.value === 'unavailable') return 'Недоступен'
  return 'Неизвестно'
})

const statusClass = computed(() => {
  if (status.value === 'pending') return 'mobile-plagiarism-card__status--pending'
  return 'mobile-plagiarism-card__status--unknown'
})

const openIfReady = () => {
  if (!isReady.value) return
  emit('open', props.item.id)
}
</script>

<style scoped>
.mobile-plagiarism-card {
  background: var(--paper);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-sizing: border-box;
  box-shadow: var(--shadow-sm);
  color: var(--ink);
  display: grid;
  gap: 12px;
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
  padding: 14px;
  text-align: left;
  width: 100%;
}

.mobile-plagiarism-card__top {
  align-items: flex-start;
  display: flex;
  gap: 12px;
  justify-content: space-between;
  min-width: 0;
}

.mobile-plagiarism-card__file {
  align-items: flex-start;
  display: flex;
  flex: 1 1 auto;
  gap: 9px;
  min-width: 0;
  overflow: hidden;
}

.mobile-plagiarism-card__file > div {
  min-width: 0;
  overflow: hidden;
}

.mobile-plagiarism-card__file svg {
  color: var(--muted);
  flex: 0 0 auto;
  margin-top: 2px;
}

.mobile-plagiarism-card__file h3 {
  font-size: 13px;
  font-weight: 650;
  line-height: 1.25;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-plagiarism-card__file p {
  color: var(--muted);
  font-size: 11px;
  margin: 3px 0 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-plagiarism-card__score {
  flex: 0 0 auto;
  font-size: 18px;
  font-weight: 800;
  line-height: 1;
}

.mobile-plagiarism-card:disabled {
  cursor: default;
}

.mobile-plagiarism-card__status {
  border-radius: 999px;
  flex: 0 0 auto;
  font-size: 10px;
  font-weight: 800;
  line-height: 1.1;
  max-width: 96px;
  padding: 5px 7px;
  text-align: center;
}

.mobile-plagiarism-card__status--pending {
  background: var(--mixed-bg);
  color: var(--mixed-ink);
}

.mobile-plagiarism-card__status--unknown {
  background: var(--bg-sunken);
  color: var(--muted);
}

.mobile-plagiarism-card__meter {
  background: var(--bg-sunken);
  border-radius: 999px;
  height: 7px;
  overflow: hidden;
}

.mobile-plagiarism-card__meter span {
  display: block;
  height: 100%;
}

.mobile-plagiarism-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

.mobile-plagiarism-card__meta span {
  background: var(--bg-sunken);
  border-radius: 999px;
  color: var(--ink-2);
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
}
</style>
