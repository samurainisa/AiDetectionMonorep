<template>
  <div class="circular-progress" :style="rootStyle">
    <svg :width="size" :height="size" class="circular-progress__svg" viewBox="0 0 100 100">
      <circle
        cx="50"
        cy="50"
        :r="radius"
        fill="none"
        stroke="#e5e7eb"
        :stroke-width="strokeWidth"
        class="circular-progress__background"
      />

      <circle
        cx="50"
        cy="50"
        :r="radius"
        fill="none"
        :stroke="strokeColor"
        :stroke-width="strokeWidth"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="strokeDashoffset"
        stroke-linecap="round"
        class="circular-progress__bar"
        transform="rotate(-90 50 50)"
      />
    </svg>

    <div class="circular-progress__text">
      <div class="circular-progress__value">{{ percentage }}%</div>
      <div class="circular-progress__label">{{ label }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  value: number
  size?: number
  strokeWidth?: number
  label?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 120,
  strokeWidth: 8,
  label: 'AI',
})

const radius = computed(() => (100 - props.strokeWidth) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const percentage = computed(() => Math.round(props.value * 100))

const strokeDashoffset = computed(() => circumference.value - props.value * circumference.value)

const strokeColor = computed(() => {
  const p = percentage.value
  if (p >= 80) return '#dc2626'
  if (p >= 50) return '#ea580c'
  if (p >= 20) return '#ca8a04'
  return '#16a34a'
})

const rootStyle = computed(() => ({
  '--cp-size': `${props.size}px`,
  '--cp-color': strokeColor.value,
}))
</script>

<style scoped>
.circular-progress {
  align-items: center;
  display: inline-flex;
  height: var(--cp-size);
  justify-content: center;
  position: relative;
  width: var(--cp-size);
}

.circular-progress__svg {
  transform: rotate(-90deg);
}

.circular-progress__bar {
  transition: stroke-dashoffset 0.5s ease-in-out;
}

.circular-progress__text {
  align-items: center;
  display: flex;
  flex-direction: column;
  inset: 0;
  justify-content: center;
  position: absolute;
  text-align: center;
}

.circular-progress__value {
  color: var(--cp-color);
  font-size: 1.125rem;
  font-weight: 700;
}

.circular-progress__label {
  color: #6b7280;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
</style>
