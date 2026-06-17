<template>
  <div class="analyzing-state">
    <div class="analyzing-state__spinner" />
    <p class="serif analyzing-state__title">Анализируем текст…</p>
    <p class="analyzing-state__subtitle">Обычно это занимает 3–8 секунд</p>
  </div>
</template>

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
</style>
