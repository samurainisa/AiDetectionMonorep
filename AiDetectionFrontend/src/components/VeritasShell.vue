<template>
  <div class="veritas-shell">
    <aside class="shell-sidebar">
      <div class="brand">
        <div class="brand__text">
          <span class="brand__title">AI-DETECTION</span>
        </div>
      </div>

      <RouterLink class="va-btn primary sidebar-cta" to="/">
        <VIcon name="plus" :size="14" />
        Новый анализ
      </RouterLink>

      <nav class="sidebar-nav">
        <div class="sidebar-nav__label">Рабочее пространство</div>
        <RouterLink
          v-for="item in primaryNav"
          :key="item.id"
          class="nav-item"
          :class="{ 'nav-item--active': active === item.id }"
          :to="item.path"
        >
          <VIcon :name="item.icon" :size="15" class="nav-item__icon" />
          <span class="nav-item__text">{{ item.label }}</span>
        </RouterLink>
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

    <nav class="mobile-tabbar" aria-label="Mobile navigation">
      <div class="mobile-tabbar__side">
        <RouterLink
          v-for="item in mobileLeftNav"
          :key="item.id"
          class="mobile-tabbar__item"
          :class="{ 'mobile-tabbar__item--active': active === item.id }"
          :to="item.path"
        >
          <VIcon :name="item.icon" :size="20" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </div>

      <RouterLink class="mobile-tabbar__fab" to="/" aria-label="New analysis">
        <VIcon name="plus" :size="24" />
        <span>Новый</span>
      </RouterLink>

      <div class="mobile-tabbar__side mobile-tabbar__side--right">
        <RouterLink
          v-for="item in mobileRightNav"
          :key="item.id"
          class="mobile-tabbar__item"
          :class="{ 'mobile-tabbar__item--active': active === item.id }"
          :to="item.path"
        >
          <VIcon :name="item.icon" :size="20" />
          <span>{{ item.label }}</span>
        </RouterLink>

        <RouterLink
          v-if="user"
          class="mobile-tabbar__item mobile-tabbar__profile"
          to="/profile"
          :title="userName"
        >
          <span class="mobile-tabbar__avatar">{{ userInitials }}</span>
          <span>Профиль</span>
        </RouterLink>
      </div>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
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

const mobileNav = computed(() => primaryNav.value.filter((item) => item.id !== 'home'))
const mobileLeftNav = computed(() => mobileNav.value.slice(0, 2))
const mobileRightNav = computed(() => mobileNav.value.slice(2, 4))

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
  margin: 0 auto;
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
  text-decoration: none;
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

.mobile-tabbar {
  display: none;
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

@media (max-width: 760px) {
  .veritas-shell {
    display: block;
    min-height: 100dvh;
  }

  .shell-sidebar {
    display: none;
  }

  .shell-main {
    min-height: 100dvh;
    padding-bottom: calc(86px + env(safe-area-inset-bottom, 0px));
  }

  .shell-topbar {
    height: 48px;
    padding: 0 14px;
  }

  .breadcrumbs {
    font-size: 12px;
    max-width: 100%;
  }

  .breadcrumbs__item {
    max-width: 42vw;
  }

  .mobile-tabbar {
    align-items: center;
    background: color-mix(in srgb, var(--paper) 94%, transparent);
    border-top: 1px solid var(--border);
    bottom: 0;
    box-shadow: 0 -8px 28px rgba(31, 29, 26, 0.1);
    display: grid;
    grid-template-columns: minmax(0, 1fr) 70px minmax(0, 1fr);
    gap: 4px;
    left: 0;
    min-height: calc(72px + env(safe-area-inset-bottom, 0px));
    padding: 8px 8px calc(8px + env(safe-area-inset-bottom, 0px));
    position: fixed;
    right: 0;
    z-index: 40;
  }

  .mobile-tabbar__side {
    align-items: end;
    display: grid;
    gap: 2px;
    grid-auto-columns: minmax(42px, 1fr);
    grid-auto-flow: column;
    min-width: 0;
  }

  .mobile-tabbar__side--right {
    grid-auto-columns: minmax(38px, 1fr);
  }

  .mobile-tabbar__item {
    align-items: center;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 12px;
    color: var(--muted);
    display: flex;
    flex-direction: column;
    font-family: var(--font-sans);
    font-size: 10px;
    font-weight: 600;
    gap: 3px;
    height: 52px;
    justify-content: center;
    line-height: 1.05;
    min-width: 0;
    padding: 4px 2px;
    text-align: center;
    text-decoration: none;
  }

  .mobile-tabbar__item span:last-child {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mobile-tabbar__item--active {
    color: var(--accent-ink);
  }

  .mobile-tabbar__item--active svg {
    color: var(--accent);
  }

  .mobile-tabbar__fab {
    align-items: center;
    align-self: start;
    background: var(--accent);
    border: 4px solid var(--bg);
    border-radius: 22px;
    box-shadow: 0 10px 24px rgba(232, 116, 61, 0.28);
    color: #fff;
    display: flex;
    flex-direction: column;
    font-family: var(--font-sans);
    font-size: 10px;
    font-weight: 700;
    gap: 1px;
    height: 62px;
    justify-content: center;
    justify-self: center;
    line-height: 1;
    margin-top: -22px;
    text-decoration: none;
    width: 62px;
  }

  .mobile-tabbar__profile {
    appearance: none;
    cursor: pointer;
  }

  .mobile-tabbar__avatar {
    align-items: center;
    background: var(--accent-bg);
    border-radius: 999px;
    color: var(--accent-ink);
    display: flex;
    font-size: 10px;
    font-weight: 700;
    height: 21px;
    justify-content: center;
    max-width: none;
    overflow: visible;
    width: 21px;
  }
}

@media (max-width: 380px) {
  .mobile-tabbar {
    grid-template-columns: minmax(0, 1fr) 62px minmax(0, 1fr);
    padding-left: 6px;
    padding-right: 6px;
  }

  .mobile-tabbar__fab {
    border-radius: 19px;
    height: 56px;
    width: 56px;
  }

  .mobile-tabbar__item {
    font-size: 9px;
    height: 50px;
  }
}
</style>
