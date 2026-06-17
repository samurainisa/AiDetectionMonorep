<template>
  <VeritasShell :breadcrumbs="breadcrumbs">
    <section class="profile-page">
      <article class="va-card profile-card">
        <div class="profile-card__header">
          <div class="profile-card__avatar">{{ initials }}</div>
          <div class="profile-card__meta">
            <h1 class="profile-card__name">{{ userName }}</h1>
            <p class="profile-card__role">{{ roleName }}</p>
          </div>
        </div>

        <dl class="profile-card__info">
          <div class="profile-card__row">
            <dt>Email</dt>
            <dd>{{ user?.email || '—' }}</dd>
          </div>
          <div class="profile-card__row">
            <dt>Роль</dt>
            <dd>{{ roleName }}</dd>
          </div>
          <div class="profile-card__row">
            <dt>ID пользователя</dt>
            <dd>{{ user?.id ?? '—' }}</dd>
          </div>
          <div class="profile-card__row">
            <dt>Статус</dt>
            <dd>{{ user?.is_active ? 'Активен' : 'Неактивен' }}</dd>
          </div>
        </dl>

        <button class="va-btn ghost profile-card__logout" type="button" @click="logout">
          Выйти из аккаунта
        </button>
      </article>
    </section>
  </VeritasShell>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import VeritasShell from '../components/VeritasShell.vue'
import { AuthService, getRoleDisplayName, getUserDisplayName } from '../services/auth'

const router = useRouter()
const breadcrumbs = [{ label: 'Профиль' }]
const user = computed(() => AuthService.getUser())
const userName = computed(() => getUserDisplayName(user.value))
const roleName = computed(() => getRoleDisplayName(user.value?.role || 'student'))
const initials = computed(() => {
  const fullName = userName.value.trim()
  if (!fullName) return 'П'
  return fullName
    .split(' ')
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
})

const logout = async () => {
  await AuthService.logout()
  await router.push('/auth')
}
</script>

<style scoped>
.profile-page {
  padding: 24px;
}

.profile-card {
  margin: 0 auto;
  max-width: 680px;
  padding: 20px;
}

.profile-card__header {
  align-items: center;
  display: flex;
  gap: 14px;
  margin-bottom: 18px;
}

.profile-card__avatar {
  align-items: center;
  background: var(--accent-bg);
  border-radius: 999px;
  color: var(--accent-ink);
  display: flex;
  font-size: 20px;
  font-weight: 700;
  height: 56px;
  justify-content: center;
  width: 56px;
}

.profile-card__name {
  font-size: 20px;
  margin: 0;
}

.profile-card__role {
  color: var(--muted);
  font-size: 13px;
  margin: 2px 0 0;
}

.profile-card__info {
  border-top: 1px solid var(--border);
  margin: 0;
  padding-top: 12px;
}

.profile-card__row {
  border-bottom: 1px solid var(--border);
  display: flex;
  font-size: 14px;
  justify-content: space-between;
  padding: 10px 0;
}

.profile-card__row dt {
  color: var(--muted);
}

.profile-card__row dd {
  margin: 0;
}

.profile-card__logout {
  margin-top: 16px;
}
</style>
