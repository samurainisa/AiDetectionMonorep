<template>
  <section class="mobile-analysis-text">
    <article class="mobile-analysis-text__card">
      <div v-if="hasWindows" class="mobile-analysis-text__content" :data-seg-mode="segMode">
        <span
          v-for="(windowItem, index) in windows"
          :key="index"
          class="seg"
          :data-p="probBucket(windowItem.ai_likelihood)"
          :data-cls="segCls(windowItem)"
          :class="{ active: activeIndex === index }"
          :title="`${segmentAiPercent(windowItem)}% ИИ`"
          @click="$emit('update:activeIndex', index)"
        >
          {{ windowItem.text }}
        </span>
      </div>

      <div v-else class="mobile-analysis-text__content mobile-analysis-text__content--plain">
        {{ extractedText }}
      </div>
    </article>

    <div class="mobile-analysis-text__legend">
      <div class="mobile-analysis-text__legend-row">
        <span class="mobile-analysis-text__pill">
          <span class="mobile-analysis-text__dot mobile-analysis-text__dot--ai">A</span>
          ИИ
        </span>
        <span class="mobile-analysis-text__pill">
          <span class="mobile-analysis-text__dot mobile-analysis-text__dot--mixed">~</span>
          Подозр.
        </span>
        <span class="mobile-analysis-text__pill">
          <span class="mobile-analysis-text__dot mobile-analysis-text__dot--human">✓</span>
          Человек
        </span>
      </div>

      <div class="mobile-analysis-text__switch">
        <button
          v-for="mode in modes"
          :key="mode.id"
          class="mobile-analysis-text__mode"
          :class="{ 'mobile-analysis-text__mode--active': segMode === mode.id }"
          type="button"
          @click="$emit('update:segMode', mode.id)"
        >
          {{ mode.label }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { WindowData } from '../../types/api'
import { segmentVerdictClass } from '../../utils/aiResult'

type SegmentModeId = 'highlight' | 'underline' | 'pills'

defineProps<{
  windows: WindowData[]
  extractedText: string
  hasWindows: boolean
  segMode: SegmentModeId
  activeIndex: number | null
  modes: Array<{ id: SegmentModeId; label: string }>
}>()

defineEmits<{
  'update:segMode': [value: SegmentModeId]
  'update:activeIndex': [value: number]
}>()

const probBucket = (value?: number) => Math.min(4, Math.floor((value || 0) * 5))
const segCls = (windowItem: WindowData) => segmentVerdictClass(windowItem)
const segmentAiPercent = (windowItem: WindowData) => Math.round((windowItem.ai_likelihood || 0) * 100)
</script>

<style scoped>
.mobile-analysis-text {
  display: none;
}

@media (max-width: 720px) {
  .mobile-analysis-text {
    display: block;
    min-width: 0;
    padding: 12px 12px 30px;
  }

  .mobile-analysis-text__card {
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow-sm);
    overflow: hidden;
  }

  .mobile-analysis-text__content {
    color: var(--ink);
    font-size: 14px;
    line-height: 1.75;
    overflow-wrap: anywhere;
    padding: 16px;
    word-break: break-word;
  }

  .mobile-analysis-text__content--plain {
    white-space: pre-wrap;
  }

  .mobile-analysis-text__legend {
    background: color-mix(in srgb, var(--paper) 96%, transparent);
    border: 1px solid var(--border);
    border-radius: 16px;
    bottom: calc(78px + env(safe-area-inset-bottom, 0px));
    box-shadow: 0 -8px 24px rgba(31, 29, 26, 0.1);
    display: grid;
    gap: 8px;
    left: 10px;
    padding: 8px;
    position: fixed;
    right: 10px;
    z-index: 39;
  }

  .mobile-analysis-text__legend-row {
    display: grid;
    gap: 6px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .mobile-analysis-text__pill {
    align-items: center;
    color: var(--ink-2);
    display: inline-flex;
    font-size: 11px;
    font-weight: 650;
    gap: 5px;
    justify-content: center;
    min-width: 0;
  }

  .mobile-analysis-text__dot {
    align-items: center;
    border-radius: 999px;
    color: #fff;
    display: inline-flex;
    flex: 0 0 auto;
    font-size: 9px;
    font-weight: 800;
    height: 16px;
    justify-content: center;
    width: 16px;
  }

  .mobile-analysis-text__dot--ai {
    background: var(--ai);
  }

  .mobile-analysis-text__dot--mixed {
    background: var(--mixed);
  }

  .mobile-analysis-text__dot--human {
    background: var(--human);
  }

  .mobile-analysis-text__switch {
    background: var(--bg-sunken);
    border-radius: 999px;
    display: grid;
    gap: 2px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    padding: 2px;
  }

  .mobile-analysis-text__mode {
    background: transparent;
    border: 0;
    border-radius: 999px;
    color: var(--muted);
    cursor: pointer;
    font: inherit;
    font-size: 11px;
    font-weight: 650;
    height: 28px;
  }

  .mobile-analysis-text__mode--active {
    background: var(--paper);
    box-shadow: var(--shadow-sm);
    color: var(--ink);
  }
}
</style>
