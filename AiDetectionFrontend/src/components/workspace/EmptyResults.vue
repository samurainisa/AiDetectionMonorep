<template>
  <div class="empty-results">
    <div class="empty-results__icon">
      <VIcon name="sparkle" :size="24" />
    </div>
    <p class="serif empty-results__title">Готовы к анализу</p>
    <p class="empty-results__subtitle">
      Результаты и посегментная разметка появятся здесь, как только вы запустите проверку.
    </p>
  </div>
</template>

<script setup lang="ts">
import VIcon from '../VIcon.vue'
</script>

<style scoped>
.empty-results {
  align-items: center;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  justify-content: center;
  padding: 40px;
  text-align: center;
}

.empty-results__icon {
  align-items: center;
  background: var(--bg-sunken);
  border-radius: 18px;
  color: var(--muted);
  display: grid;
  height: 64px;
  place-items: center;
  width: 64px;
}

.empty-results__title {
  font-size: 22px;
  font-weight: 400;
  margin: 0;
}

.empty-results__subtitle {
  color: var(--muted);
  font-size: 13px;
  margin: 0;
  max-width: 300px;
}
</style>
