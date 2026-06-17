<template>
  <div class="analyzing-state">
    <div class="analyzing-state__spinner" />
    <p class="serif analyzing-state__title">{{ title }}</p>
    <p class="analyzing-state__subtitle">{{ subtitle }}</p>

    <div class="analyzing-state__progress" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100">
      <span :style="{ width: `${progress}%` }" />
    </div>

    <p class="analyzing-state__meta">
      <span v-if="remainingSeconds > 0" class="tnum">Осталось примерно {{ remainingSeconds }} сек.</span>
      <span v-else>Результат уже в пути, финализируем обработку.</span>
    </p>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    subtitle?: string
    progress?: number
    remainingSeconds?: number
  }>(),
  {
    title: 'Анализируем текст...',
    subtitle: 'Время рассчитано по размеру документа',
    progress: 8,
    remainingSeconds: 0,
  },
)
</script>

<style scoped>
.analyzing-state {
  align-items: center;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  justify-content: center;
}

.analyzing-state__spinner {
  animation: va-spin 0.8s linear infinite;
  border: 3px solid rgba(232, 116, 61, 0.2);
  border-radius: 50%;
  border-top-color: var(--accent);
  height: 80px;
  width: 80px;
}

.analyzing-state__title {
  font-size: 20px;
  font-weight: 400;
  margin: 0;
}

.analyzing-state__subtitle {
  color: var(--muted);
  font-size: 13px;
  margin: 0;
}

.analyzing-state__progress {
  background: var(--bg-sunken);
  border-radius: 999px;
  height: 7px;
  margin-top: 2px;
  overflow: hidden;
  width: min(220px, 72vw);
}

.analyzing-state__progress span {
  background: linear-gradient(90deg, var(--accent), var(--mixed));
  border-radius: inherit;
  display: block;
  height: 100%;
  min-width: 8px;
  transition: width 0.25s ease;
}

.analyzing-state__meta {
  color: var(--ink-2);
  font-size: 12px;
  font-weight: 600;
  margin: -4px 0 0;
}
</style>
