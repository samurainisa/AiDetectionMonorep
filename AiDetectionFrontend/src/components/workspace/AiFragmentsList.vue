<template>
  <div class="ai-fragments">
    <div v-if="flagged.length" class="ai-fragments__list va-scroll">
      <article v-for="(item, index) in flagged" :key="index" class="ai-fragments__item" :data-cls="item.verdict">
        <header class="ai-fragments__head">
          <span class="va-chip" :class="item.verdict">
            <span class="va-dot" :class="item.verdict" />
            {{ item.label }}
          </span>
          <span class="tnum ai-fragments__pct">{{ item.percent }}% ИИ</span>
        </header>
        <p class="ai-fragments__text">{{ item.text }}</p>
      </article>
    </div>

    <p v-else class="ai-fragments__empty">
      Подозрительных ИИ-фрагментов не обнаружено.
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WindowData } from '../../types/api'
import { resolveSegmentVerdict, segmentVerdictLabel } from '../../utils/aiResult'

const props = withDefaults(
  defineProps<{
    windows?: WindowData[] | null
    limit?: number
  }>(),
  { windows: () => [], limit: 30 },
)

const flagged = computed(() => {
  const items = (props.windows ?? [])
    .map((windowItem) => ({
      windowItem,
      verdict: resolveSegmentVerdict(windowItem),
      likelihood: windowItem.ai_likelihood ?? 0,
    }))
    .filter((entry) => entry.verdict !== 'human' && (entry.windowItem.text || '').trim().length > 0)
    .sort((a, b) => b.likelihood - a.likelihood)
    .slice(0, props.limit)

  return items.map((entry) => ({
    text: entry.windowItem.text,
    verdict: entry.verdict,
    label: segmentVerdictLabel(entry.windowItem),
    percent: Math.round(entry.likelihood * 100),
  }))
})
</script>

<style scoped>
.ai-fragments__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 380px;
  overflow: auto;
}

.ai-fragments__item {
  background: var(--bg-sunken);
  border-left: 3px solid var(--mixed);
  border-radius: 8px;
  padding: 10px 12px;
}

.ai-fragments__item[data-cls='ai'] {
  border-left-color: var(--ai);
}

.ai-fragments__item[data-cls='mixed'] {
  border-left-color: var(--mixed);
}

.ai-fragments__head {
  align-items: center;
  display: flex;
  gap: 10px;
  justify-content: space-between;
  margin-bottom: 6px;
}

.ai-fragments__pct {
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

.ai-fragments__text {
  color: var(--ink);
  font-size: 13px;
  line-height: 1.55;
  margin: 0;
}

.ai-fragments__empty {
  color: var(--muted);
  font-size: 13px;
  margin: 0;
  padding: 16px 0;
  text-align: center;
}
</style>
