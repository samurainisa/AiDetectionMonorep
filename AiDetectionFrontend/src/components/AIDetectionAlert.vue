<template>
  <Dialog
    v-model:visible="visible"
    :modal="true"
    :closable="true"
    :draggable="false"
    header=""
    class="ai-detection-dialog"
  >
    <div class="text-center p-6">
      <!-- Иконка предупреждения -->
      <div class="mb-4">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full">
          <svg class="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
            ></path>
          </svg>
        </div>
      </div>

      <!-- Заголовок -->
      <h3 class="text-xl font-bold text-red-600 mb-2">AI Detected</h3>

      <p class="text-gray-600 mb-6">Искусственный интеллект обнаружен</p>

      <!-- Статистика -->
      <div class="grid grid-cols-2 gap-4 mb-6">
        <div class="bg-red-50 rounded-lg p-4">
          <div class="text-2xl font-bold text-red-600">{{ aiSegments }}/{{ totalSegments }}</div>
          <div class="text-xs text-red-500 uppercase tracking-wide">AI SEGMENTS</div>
        </div>
        <div class="bg-red-50 rounded-lg p-4">
          <div class="text-2xl font-bold text-red-600">{{ confidence }}%</div>
          <div class="text-xs text-red-500 uppercase tracking-wide">CONFIDENCE</div>
        </div>
      </div>

      <!-- Кнопки -->
      <div class="flex gap-3">
        <Button @click="closeDialog" label="Закрыть" outlined class="flex-1" />
        <Button
          @click="viewDetails"
          label="Подробности"
          class="flex-1 bg-red-600 hover:bg-red-700 text-white"
        />
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'

interface Props {
  modelValue: boolean
  aiSegments: number
  totalSegments: number
  confidence: number
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'viewDetails'): void
}

const props = withDefaults(defineProps<Props>(), {
  aiSegments: 0,
  totalSegments: 0,
  confidence: 0,
})

const emit = defineEmits<Emits>()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const closeDialog = () => {
  visible.value = false
}

const viewDetails = () => {
  emit('viewDetails')
  visible.value = false
}
</script>

<style scoped>
:deep(.ai-detection-dialog) {
  width: 400px;
}

:deep(.ai-detection-dialog .p-dialog-header) {
  display: none;
}

:deep(.ai-detection-dialog .p-dialog-content) {
  padding: 0;
  border-radius: 0.75rem;
}
</style>
