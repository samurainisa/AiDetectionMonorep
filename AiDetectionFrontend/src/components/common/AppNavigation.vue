<template>
  <div class="mb-8">
    <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
      <div>
        <h1 class="text-3xl font-bold text-black mb-2">{{ title }}</h1>
        <p class="text-gray-600">{{ description }}</p>
        <div v-if="$slots.subtitle" class="mt-2">
          <slot name="subtitle" />
        </div>
      </div>
      <div v-if="$slots.actions" class="flex flex-wrap gap-3">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title: string
  description: string
}

defineProps<Props>()
</script>
