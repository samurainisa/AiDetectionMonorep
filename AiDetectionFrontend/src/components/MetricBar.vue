<template>
  <div class="metric-bar">
    <div class="metric-bar__header">
      <span class="metric-bar__label">{{ label }}</span>
      <span class="tnum metric-bar__value">{{ Math.round(value * 100) }}%</span>
    </div>

    <div class="metric-bar__track">
      <div class="metric-bar__fill" :style="fillStyle" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ label: string; value: number; color: string }>()

const fillStyle = computed(() => ({
  width: `${props.value * 100}%`,
  background: props.color,
}))
</script>

<style scoped>
.metric-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.metric-bar__header {
  align-items: baseline;
  display: flex;
  justify-content: space-between;
}

.metric-bar__label {
  color: var(--muted);
  font-size: 12px;
}

.metric-bar__value {
  font-size: 13px;
  font-weight: 500;
}

.metric-bar__track {
  background: var(--bg-sunken);
  border-radius: 999px;
  height: 4px;
  overflow: hidden;
}

.metric-bar__fill {
  border-radius: 999px;
  height: 100%;
}
</style>
