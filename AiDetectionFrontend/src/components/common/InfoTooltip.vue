<template>
  <div class="inline-flex items-center gap-1 cursor-help" v-tooltip.top="tooltip">
    <slot />
    <i class="pi pi-info-circle text-gray-400 text-xs hover:text-blue-500 transition-colors"></i>
  </div>
</template>

<script setup lang="ts">
interface Props {
  tooltip: string
}

defineProps<Props>()
</script>

<style scoped>
.cursor-help {
  cursor: help;
}
</style>
