<template>
  <div class="min-h-screen flex items-center justify-center bg-white">
    <div class="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-lg border border-gray-200">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">Войти в систему</h2>
        <p class="mt-2 text-center text-sm text-gray-700">Система детекции ИИ контента</p>
      </div>

      <form class="mt-8 space-y-6" @submit.prevent="handleSubmit">
        <div class="space-y-4">
          <div>
            <label for="email" class="block text-sm font-medium text-gray-900 mb-1">Email</label>
            <input
              id="email"
              v-model="form.email"
              name="email"
              type="email"
              required
              class="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 bg-white rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 sm:text-sm"
              placeholder="Email адрес"
            />
          </div>
          <div>
            <label for="password" class="block text-sm font-medium text-gray-900 mb-1"
              >Пароль</label
            >
            <input
              id="password"
              v-model="form.password"
              name="password"
              type="password"
              required
              class="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 bg-white rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 sm:text-sm"
              placeholder="Пароль"
            />
          </div>
        </div>

        <div v-if="error" class="text-red-600 text-sm text-center bg-red-50 p-3 rounded-md">
          {{ error }}
        </div>

        <div>
          <button
            type="submit"
            :disabled="isLoading"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 transition-colors"
          >
            <span v-if="isLoading">Вход...</span>
            <span v-else>Войти</span>
          </button>
        </div>

        <div class="text-center">
          <button
            type="button"
            @click="$emit('switchToRegister')"
            class="text-green-600 hover:text-green-700 text-sm transition-colors"
          >
            Нет аккаунта? Зарегистрироваться
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { AuthService } from '../services/auth'

// Эмиты
const emit = defineEmits<{
  switchToRegister: []
  loginSuccess: []
}>()

// Реактивные данные
const isLoading = ref(false)
const error = ref('')

const form = reactive({
  email: '',
  password: '',
})

// Обработка отправки формы
const handleSubmit = async () => {
  if (isLoading.value) return

  error.value = ''
  isLoading.value = true

  try {
    await AuthService.login({
      email: form.email,
      password: form.password,
    })

    emit('loginSuccess')
  } catch (err: any) {
    error.value = err?.error || 'Произошла ошибка при входе'
    console.error('Login error:', err)
  } finally {
    isLoading.value = false
  }
}
</script>
