<template>
  <div class="min-h-screen flex items-center justify-center bg-white">
    <div class="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-lg border border-gray-200">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Регистрация
        </h2>
        <p class="mt-2 text-center text-sm text-gray-700">
          Создать новый аккаунт в системе
        </p>
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
            <label for="firstName" class="block text-sm font-medium text-gray-900 mb-1">Имя</label>
            <input
              id="firstName"
              v-model="form.first_name"
              name="firstName"
              type="text"
              required
              class="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 bg-white rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 sm:text-sm"
              placeholder="Ваше имя"
            />
          </div>
          
          <div>
            <label for="lastName" class="block text-sm font-medium text-gray-900 mb-1">Фамилия</label>
            <input
              id="lastName"
              v-model="form.last_name"
              name="lastName"
              type="text"
              required
              class="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 bg-white rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 sm:text-sm"
              placeholder="Ваша фамилия"
            />
          </div>
          
          <div>
            <label for="role" class="block text-sm font-medium text-gray-900 mb-1">Роль</label>
            <select
              id="role"
              v-model="form.role"
              name="role"
              required
              class="block w-full px-3 py-2 border border-gray-300 bg-white text-gray-900 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 sm:text-sm"
            >
              <option value="student">Студент</option>
              <option value="teacher">Преподаватель</option>
            </select>
          </div>
          
          <div v-if="form.role === 'student'">
            <label for="studentId" class="block text-sm font-medium text-gray-900 mb-1">Номер студенческого билета</label>
            <input
              id="studentId"
              v-model="form.student_id"
              name="studentId"
              type="text"
              class="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 bg-white rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 sm:text-sm"
              placeholder="Например: 20230001"
            />
          </div>
          
          <div>
            <label for="password" class="block text-sm font-medium text-gray-900 mb-1">Пароль</label>
            <input
              id="password"
              v-model="form.password"
              name="password"
              type="password"
              required
              class="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 bg-white rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 sm:text-sm"
              placeholder="Пароль (минимум 6 символов)"
              minlength="6"
            />
          </div>
          
          <div>
            <label for="confirmPassword" class="block text-sm font-medium text-gray-900 mb-1">Подтверждение пароля</label>
            <input
              id="confirmPassword"
              v-model="form.confirmPassword"
              name="confirmPassword"
              type="password"
              required
              class="appearance-none relative block w-full px-3 py-2 border border-gray-300 text-gray-900 bg-white rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 sm:text-sm"
              placeholder="Повторите пароль"
            />
          </div>
        </div>

        <div v-if="error" class="text-red-600 text-sm text-center bg-red-50 p-3 rounded-md">
          {{ error }}
        </div>

        <div>
          <button
            type="submit"
            :disabled="isLoading || !isFormValid"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 transition-colors"
          >
            <span v-if="isLoading">Регистрация...</span>
            <span v-else>Зарегистрироваться</span>
          </button>
        </div>

        <div class="text-center">
          <button
            type="button"
            @click="$emit('switchToLogin')"
            class="text-green-600 hover:text-green-700 text-sm transition-colors"
          >
            Уже есть аккаунт? Войти
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { AuthService } from '../services/auth'

// Эмиты
const emit = defineEmits<{
  switchToLogin: []
  registerSuccess: []
}>()

// Реактивные данные
const isLoading = ref(false)
const error = ref('')

const form = reactive({
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  confirmPassword: '',
  role: 'student' as 'student' | 'teacher',
  student_id: ''
})

// Валидация формы
const isFormValid = computed(() => {
  return form.email && 
         form.first_name && 
         form.last_name && 
         form.password && 
         form.confirmPassword &&
         form.password === form.confirmPassword &&
         form.password.length >= 6
})

// Обработка отправки формы
const handleSubmit = async () => {
  if (isLoading.value || !isFormValid.value) return

  // Проверка совпадения паролей
  if (form.password !== form.confirmPassword) {
    error.value = 'Пароли не совпадают'
    return
  }

  error.value = ''
  isLoading.value = true

  try {
    const registerData: any = {
      email: form.email.toLowerCase().trim(),
      password: form.password,
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      role: form.role
    }

    // Добавляем student_id если указан
    if (form.role === 'student' && form.student_id.trim()) {
      registerData.student_id = form.student_id.trim()
    }

    await AuthService.register(registerData)

    emit('registerSuccess')
  } catch (err: any) {
    error.value = err?.error || 'Произошла ошибка при регистрации'
    console.error('Registration error:', err)
  } finally {
    isLoading.value = false
  }
}
</script>