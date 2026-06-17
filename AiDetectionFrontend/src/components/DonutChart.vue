<template>
  <div class="donut-chart" :style="chartStyle">
    <svg :width="size" :height="size" class="donut-chart__svg">
      <circle :cx="cx" :cy="cx" :r="r" stroke="var(--bg-sunken)" :stroke-width="stroke" fill="none" />
      <circle
        v-for="(segment, index) in segments"
        :key="index"
        :cx="cx"
        :cy="cx"
        :r="r"
        :stroke="segment.color"
        :stroke-width="stroke"
        fill="none"
        :stroke-dasharray="`${segment.length} ${circumference - segment.length}`"
        :stroke-dashoffset="-segment.offset"
        stroke-linecap="butt"
      />
    </svg>

    <div class="donut-chart__center">
      <slot>
        <div class="donut-chart__center-content">
          <div class="tnum donut-chart__value" :style="valueStyle">
            {{ aiPercent }}%
          </div>
          <div class="donut-chart__label">Вероятность ИИ</div>
          <div v-if="hasMixed" class="donut-chart__mixed">
            <span>Смеш.</span>
            <strong class="tnum">{{ mixedPercent }}%</strong>
          </div>
        </div>
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface SegmentData {
  value: number
  color: string
}

interface DonutSegment extends SegmentData {
  length: number
  offset: number
}

const props = withDefaults(
  defineProps<{
    size?: number
    stroke?: number
    ai?: number
    human?: number
    uncertain?: number
  }>(),
  {
    size: 180,
    stroke: 16,
    ai: 0,
    human: 0,
    uncertain: 0,
  },
)

const r = computed(() => (props.size - props.stroke) / 2)
const cx = computed(() => props.size / 2)
const circumference = computed(() => 2 * Math.PI * r.value)

const chartStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
}))

const valueStyle = computed(() => ({
  fontSize: `${props.size * 0.26}px`,
}))

const aiPercent = computed(() => Math.round(props.ai * 100))
const mixedPercent = computed(() => Math.round(props.uncertain * 100))
const hasMixed = computed(() => mixedPercent.value > 0)

const segments = computed<DonutSegment[]>(() => {
  const items: SegmentData[] = [
    { value: props.human, color: 'var(--human)' },
    { value: props.uncertain, color: 'var(--mixed)' },
    { value: props.ai, color: 'var(--ai)' },
  ]

  let offset = 0
  return items.map((item) => {
    const length = item.value * circumference.value
    const segment: DonutSegment = {
      ...item,
      length,
      offset,
    }
    offset += length
    return segment
  })
})
</script>

<style scoped>
.donut-chart {
  position: relative;
}

.donut-chart__svg {
  transform: rotate(-90deg);
}

.donut-chart__center {
  display: grid;
  inset: 0;
  place-items: center;
  position: absolute;
  text-align: center;
}

.donut-chart__center-content {
  min-width: 0;
}

.donut-chart__value {
  color: var(--ink);
  font-weight: 600;
  letter-spacing: 0;
  line-height: 1;
}

.donut-chart__label {
  color: var(--muted);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  margin-top: 5px;
  text-transform: uppercase;
}

.donut-chart__mixed {
  align-items: center;
  color: var(--mixed-ink);
  display: inline-flex;
  font-size: 10px;
  font-weight: 700;
  gap: 4px;
  justify-content: center;
  line-height: 1.1;
  margin-top: 5px;
  max-width: 100%;
  white-space: nowrap;
}

.donut-chart__mixed::before {
  background: var(--mixed);
  border-radius: 999px;
  content: '';
  height: 6px;
  width: 6px;
}
</style>
