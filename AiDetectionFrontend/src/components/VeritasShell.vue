<template>
  <div class="veritas-shell">
    <aside class="shell-sidebar">
      <div class="brand">
        <div class="brand__text">
          <span class="brand__title">AI-DETECTION</span>
        </div>
      </div>

      <button class="va-btn primary sidebar-cta" type="button" @click="router.push('/')">
        <VIcon name="plus" :size="14" />
        Новый анализ
      </button>

      <nav class="sidebar-nav">
        <div class="sidebar-nav__label">Рабочее пространство</div>
        <button
          v-for="item in primaryNav"
          :key="item.id"
          class="nav-item"
          :class="{ 'nav-item--active': active === item.id }"
          type="button"
          @click="router.push(item.path)"
        >
          <VIcon :name="item.icon" :size="15" class="nav-item__icon" />
          <span class="nav-item__text">{{ item.label }}</span>
        </button>
      </nav>

      <div class="sidebar-spacer" />

      <div v-if="user" class="sidebar-user">
        <div class="sidebar-user__avatar">{{ userInitials }}</div>
        <div class="sidebar-user__meta">
          <span class="sidebar-user__name">{{ userName }}</span>
          <span class="sidebar-user__role">{{ userRole }}</span>
        </div>
        <button class="va-btn ghost icon-btn icon-btn--sm" type="button" title="Выйти" @click="logout">
          <VIcon name="x" :size="13" />
        </button>
      </div>
    </aside>

    <main class="shell-main">
      <header class="shell-topbar">
        <div v-if="breadcrumbs && breadcrumbs.length" class="breadcrumbs">
          <template v-for="(item, index) in breadcrumbs" :key="index">
            <VIcon v-if="index > 0" name="chevRight" :size="12" class="breadcrumbs__sep" />
            <span
              class="breadcrumbs__item"
              :class="{
                'breadcrumbs__item--current': index === breadcrumbs.length - 1,
                'breadcrumbs__item--clickable': Boolean(item.onClick),
              }"
              @click="item.onClick && item.onClick()"
            >
              {{ item.label }}
            </span>
          </template>
        </div>

        <div class="shell-topbar__spacer" />

      </header>

      <div class="shell-content">
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import VIcon from './VIcon.vue'
import { AuthService, getUserDisplayName, getRoleDisplayName } from '../services/auth'

interface BreadcrumbItem {
  label: string
  onClick?: () => void
}

interface NavItem {
  id: string
  label: string
  path: string
  icon: string
}

defineProps<{
  breadcrumbs?: BreadcrumbItem[]
  active?: string
}>()

const router = useRouter()

const user = computed(() => AuthService.getUser())
const userName = computed(() => getUserDisplayName(user.value))
const userRole = computed(() => (user.value ? getRoleDisplayName(user.value.role) : 'Пользователь'))

// Навигация зависит от роли: студент проверяет свои работы,
// преподаватель работает с пакетной проверкой и журналом группы.
const primaryNav = computed<NavItem[]>(() => {
  const role = user.value?.role
  const isTeacherLike = role === 'teacher' || role === 'admin'

  const items: NavItem[] = [
    { id: 'home', label: 'Анализ текста', path: '/', icon: 'sparkle' },
    { id: 'batch', label: 'Пакетная проверка', path: '/batch', icon: 'layers' },
    { id: 'history', label: isTeacherLike ? 'Журнал проверок' : 'Мои проверки', path: '/history', icon: 'history' },
    { id: 'plagiarism', label: 'Антиплагиат', path: '/plagiarism', icon: 'shield' },
  ]

  if (role === 'developer') {
    items.push({ id: 'detector', label: 'Датасет', path: '/detector', icon: 'grid' })
  }

  return items
})
const userInitials = computed(() => {
  const currentUser = user.value
  if (!currentUser) return 'АП'
  const fullName = currentUser.full_name || `${currentUser.first_name} ${currentUser.last_name}`
  return (
    fullName
      .split(' ')
      .map((part: string) => part[0])
      .join('')
      .slice(0, 2)
      .toUpperCase() || 'АП'
  )
})

const logout = async () => {
  await AuthService.logout()
  await router.push('/auth')
}
</script>

<style scoped>
.veritas-shell {
  background: var(--bg);
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 100vh;
}

.shell-sidebar {
  background: var(--bg);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 18px;
  height: 100vh;
  padding: 20px 14px;
  position: sticky;
  top: 0;
}

.brand {
  align-items: center;
  display: flex;
  gap: 10px;
  padding: 4px 6px;
}

.brand__mark {
  background: var(--ink);
  border-radius: 7px;
  color: #fff;
  display: grid;
  font-family: var(--font-serif);
  font-size: 18px;
  height: 28px;
  line-height: 1;
  padding-top: 2px;
  place-items: center;
  width: 28px;
}

.brand__text {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}

.brand__title {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.brand__subtitle {
  color: var(--muted);
  font-size: 11px;
}

.sidebar-cta {
  height: 36px;
  justify-content: center;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-nav__label {
  color: var(--muted-2);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  padding: 0 8px 6px;
  text-transform: uppercase;
}

.nav-item {
  align-items: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--ink-2);
  cursor: pointer;
  display: flex;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 400;
  gap: 10px;
  height: 34px;
  padding: 0 10px;
  text-align: left;
  width: 100%;
}

.nav-item--active {
  background: var(--paper);
  border-color: var(--border);
  box-shadow: var(--shadow-sm);
  color: var(--ink);
  font-weight: 500;
}

.nav-item__icon {
  flex-shrink: 0;
}

.nav-item__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-spacer {
  flex: 1;
}

.sidebar-user {
  align-items: center;
  border-top: 1px solid var(--border);
  display: flex;
  gap: 10px;
  padding: 8px 6px;
}

.sidebar-user__avatar {
  align-items: center;
  background: var(--accent-bg);
  border-radius: 999px;
  color: var(--accent-ink);
  display: flex;
  font-size: 12px;
  font-weight: 600;
  height: 30px;
  justify-content: center;
  width: 30px;
}

.sidebar-user__meta {
  display: flex;
  flex: 1;
  flex-direction: column;
  line-height: 1.2;
  min-width: 0;
}

.sidebar-user__name {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-user__role {
  color: var(--muted);
  font-size: 11px;
}

.icon-btn {
  justify-content: center;
  padding: 0;
}

.icon-btn--sm {
  height: 28px;
  width: 28px;
}

.icon-btn--md {
  width: 36px;
}

.shell-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.shell-topbar {
  align-items: center;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 16px;
  height: 56px;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.breadcrumbs {
  align-items: center;
  color: var(--muted);
  display: flex;
  font-size: 13px;
  gap: 6px;
  min-width: 0;
}

.breadcrumbs__sep {
  color: var(--muted-2);
}

.breadcrumbs__item {
  color: var(--muted);
  font-weight: 400;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.breadcrumbs__item--clickable {
  cursor: pointer;
}

.breadcrumbs__item--current {
  color: var(--ink);
  font-weight: 500;
}

.shell-topbar__spacer {
  flex: 1;
}

.shell-content {
  flex: 1;
  min-height: 0;
}

@media (max-width: 1080px) {
  .veritas-shell {
    grid-template-columns: 1fr;
  }

  .shell-sidebar {
    border-right: none;
    border-bottom: 1px solid var(--border);
    height: auto;
    position: static;
  }
}
</style>
