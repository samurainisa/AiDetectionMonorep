<template>
  <nav v-if="shouldShowNavigation" class="bg-white shadow-md mb-8">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <!-- Логотип -->
        <div class="flex-shrink-0">
          <RouterLink to="/" class="text-xl font-bold text-green-600"> AI Detector </RouterLink>
        </div>

        <!-- Навигационные ссылки (десктоп) -->
        <div class="hidden md:block">
          <div class="ml-10 flex items-baseline space-x-4">
            <RouterLink
              v-for="link in navLinks"
              :key="link.path"
              :to="link.path"
              class="text-gray-700 hover:text-green-600 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              :class="{ 'text-green-600 bg-green-50': isActiveRoute(link.path) }"
            >
              {{ link.name }}
            </RouterLink>
          </div>
        </div>

        <!-- Пользовательское меню (десктоп) -->
        <div class="hidden md:flex items-center space-x-4">
          <span class="text-sm text-gray-700">
            {{ userDisplayName }}
          </span>
          <span class="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
            {{ userRoleDisplay }}
          </span>
          <Button
            @click="handleLogout"
            icon="pi pi-sign-out"
            label="Выйти"
            class="p-button-text p-button-sm text-gray-600 hover:text-red-600"
            size="small"
          />
        </div>

        <!-- Кнопка бургер-меню (мобильная) -->
        <div class="md:hidden">
          <Button
            @click="toggleMobileMenu"
            :icon="isMobileMenuOpen ? 'pi pi-times' : 'pi pi-bars'"
            class="p-2 text-gray-600 hover:text-gray-800"
            text
          />
        </div>
      </div>

      <!-- Мобильное меню -->
      <div v-if="isMobileMenuOpen" class="md:hidden">
        <div class="px-2 pt-2 pb-3 space-y-1 sm:px-3 border-t border-gray-200">
          <RouterLink
            v-for="link in navLinks"
            :key="link.path"
            :to="link.path"
            @click="closeMobileMenu"
            class="text-gray-700 hover:text-green-600 block px-3 py-2 rounded-md text-base font-medium transition-colors"
            :class="{ 'text-green-600 bg-green-50': isActiveRoute(link.path) }"
          >
            {{ link.name }}
          </RouterLink>

          <!-- Пользовательское меню (мобильное) -->
          <div class="border-t border-gray-200 pt-2 mt-2">
            <div class="px-3 py-2">
              <div class="text-sm text-gray-700">{{ userDisplayName }}</div>
              <div class="text-xs text-gray-500">{{ userRoleDisplay }}</div>
            </div>
            <button
              @click="handleLogout"
              class="text-red-600 hover:text-red-800 block px-3 py-2 rounded-md text-base font-medium transition-colors w-full text-left"
            >
              Выйти
            </button>
          </div>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
// Core
import { ref, computed } from 'vue'
// Router
import { useRoute, useRouter } from 'vue-router'
// Components
import Button from 'primevue/button'
// Services
import { AuthService, getUserDisplayName, getRoleDisplayName } from '../../services/auth'

const route = useRoute()
const router = useRouter()
const isMobileMenuOpen = ref(false)

const navLinks = computed(() => {
  const isDeveloper = AuthService.hasRole('developer')
  const links = [
    { name: 'Главная', path: '/' },
    { name: 'Множественный анализ', path: '/batch' },
    { name: 'История анализов', path: '/history' },
  ]
  return isDeveloper ? [{ name: 'Датасет', path: '/detector' }, ...links] : links
})

// Проверяем, нужно ли показывать навигацию (скрываем на странице авторизации)
const shouldShowNavigation = computed(() => {
  return route.name !== 'auth' && AuthService.isAuthenticated()
})

// Получаем данные пользователя
const currentUser = computed(() => AuthService.getUser())

const userDisplayName = computed(() => {
  return getUserDisplayName(currentUser.value)
})

const userRoleDisplay = computed(() => {
  return currentUser.value ? getRoleDisplayName(currentUser.value.role) : ''
})

const isActiveRoute = (path: string) => {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(path)
}

const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

const closeMobileMenu = () => {
  isMobileMenuOpen.value = false
}

const handleLogout = async () => {
  try {
    await AuthService.logout()
    router.push('/auth')
  } catch (error) {
    console.error('Ошибка выхода:', error)
    // В любом случае перенаправляем на страницу авторизации
    router.push('/auth')
  }
}
</script>
