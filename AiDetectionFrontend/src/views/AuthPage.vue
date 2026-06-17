<template>
  <main class="auth-page">
    <section class="auth-hero" aria-label="AI Detection">
      <div class="auth-brand">
        <div class="auth-brand__mark">
          <VIcon name="sparkle" :size="18" />
        </div>
        <div>
          <div class="auth-brand__title">AI Detection</div>
          <div class="auth-brand__subtitle">Платформа проверки текстов</div>
          <div class="auth-brand__caption">ИИ-фрагменты, плагиат и пакетная обработка</div>
        </div>
      </div>

      <div class="auth-hero__content">
        <div class="auth-kicker">Проверка текста, файлов и источников</div>
        <h1 class="auth-title">Понимайте происхождение текста до принятия решения.</h1>
        <p class="auth-copy">
          Сервис помогает находить ИИ-фрагменты, проверять документы на заимствования и быстро
          разбирать большие пакеты работ в одном рабочем пространстве.
        </p>

        <div class="auth-feature-list">
          <article v-for="feature in features" :key="feature.title" class="auth-feature">
            <div class="auth-feature__icon">
              <VIcon :name="feature.icon" :size="16" />
            </div>
            <div>
              <h2>{{ feature.title }}</h2>
              <p>{{ feature.sub }}</p>
            </div>
          </article>
        </div>
      </div>

      <div class="auth-metrics" aria-label="Ключевые возможности">
        <div>
          <span>50</span>
          <p>файлов в пакете</p>
        </div>
        <div>
          <span>AI</span>
          <p>посегментная оценка</p>
        </div>
        <div>
          <span>PDF</span>
          <p>отчёты и разбор</p>
        </div>
      </div>
    </section>

    <section class="auth-panel" aria-label="Авторизация">
      <div class="auth-card">
        <div class="auth-card__header">
          <div class="auth-card__eyebrow">{{ tab === 'login' ? 'Вход' : 'Регистрация' }}</div>
          <h2>{{ tab === 'login' ? 'Продолжить работу' : 'Создать аккаунт' }}</h2>
          <p>
            {{
              tab === 'login'
                ? 'Введите данные, чтобы открыть свои проверки и новые анализы.'
                : 'Заполните профиль, чтобы начать проверять тексты и документы.'
            }}
          </p>
        </div>

        <div class="auth-tabs" role="tablist" aria-label="Режим авторизации">
          <button
            v-for="item in tabs"
            :key="item.id"
            class="auth-tabs__button"
            :class="{ 'auth-tabs__button--active': tab === item.id }"
            type="button"
            @click="tab = item.id"
          >
            {{ item.label }}
          </button>
        </div>

        <div v-if="errorMsg" class="auth-error">
          {{ errorMsg }}
        </div>

        <form class="auth-form" @submit.prevent="submit">
          <template v-if="tab === 'register'">
            <label class="auth-field">
              <span>Имя</span>
              <input v-model="form.first_name" class="va-input" placeholder="Анна" required />
            </label>

            <label class="auth-field">
              <span>Фамилия</span>
              <input v-model="form.last_name" class="va-input" placeholder="Петрова" required />
            </label>
          </template>

          <label class="auth-field">
            <span>Почта</span>
            <input
              v-model="form.email"
              class="va-input"
              type="email"
              autocomplete="email"
              required
            />
          </label>

          <label class="auth-field">
            <span>Пароль</span>
            <input
              v-model="form.password"
              class="va-input"
              type="password"
              autocomplete="current-password"
              required
              minlength="6"
            />
          </label>

          <label v-if="tab === 'register'" class="auth-field">
            <span>Роль</span>
            <select v-model="form.role" class="va-input">
              <option value="student">Студент</option>
              <option value="teacher">Преподаватель</option>
            </select>
          </label>

          <button class="va-btn accent auth-submit" type="submit" :disabled="isLoading">
            <span v-if="isLoading" class="va-spinner" />
            {{ tab === 'login' ? 'Войти' : 'Создать аккаунт' }}
          </button>
        </form>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import VIcon from '../components/VIcon.vue'
import { AuthService, defaultRouteForRole } from '../services/auth'

const router = useRouter()
const tab = ref<'login' | 'register'>('login')
const isLoading = ref(false)
const errorMsg = ref('')

const tabs = [
  { id: 'login' as const, label: 'Войти' },
  { id: 'register' as const, label: 'Регистрация' },
]

const features = [
  {
    icon: 'sparkle',
    title: 'ИИ-фрагменты',
    sub: 'Разметка показывает, какие части текста выглядят машинно сгенерированными.',
  },
  {
    icon: 'shield',
    title: 'Антиплагиат',
    sub: 'Проверка совпадений, похожих документов и источников для полного отчёта.',
  },
  {
    icon: 'layers',
    title: 'Пакетная проверка',
    sub: 'Загрузка группы файлов и единая сводка по результатам обработки.',
  },
]

const form = reactive({
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: 'student' as 'student' | 'teacher',
})

onMounted(() => {
  if (AuthService.isAuthenticated()) router.push(defaultRouteForRole(AuthService.getUser()?.role))
})

const submit = async () => {
  isLoading.value = true
  errorMsg.value = ''

  try {
    if (tab.value === 'login') {
      await AuthService.login({ email: form.email, password: form.password })
    } else {
      await AuthService.register({
        email: form.email,
        password: form.password,
        first_name: form.first_name,
        last_name: form.last_name,
        role: form.role,
      })
    }

    router.push(defaultRouteForRole(AuthService.getUser()?.role))
  } catch (e: any) {
    errorMsg.value = e.error || 'Не удалось выполнить вход. Проверьте данные и попробуйте ещё раз.'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  background: var(--bg);
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(420px, 0.9fr);
  min-height: 100vh;
}

.auth-hero {
  background:
    radial-gradient(circle at 76% 18%, rgba(56, 189, 248, 0.18), transparent 28%),
    radial-gradient(circle at 18% 78%, rgba(232, 116, 61, 0.18), transparent 26%),
    linear-gradient(155deg, #101114 0%, #1f1d1a 56%, #2a2722 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  overflow: hidden;
  padding: 40px 52px;
  position: relative;
}

.auth-hero::after {
  background:
    linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 42px 42px;
  content: '';
  inset: 0;
  mask-image: linear-gradient(140deg, transparent 0%, #000 34%, transparent 100%);
  opacity: 0.35;
  position: absolute;
}

.auth-brand,
.auth-hero__content,
.auth-metrics {
  position: relative;
  z-index: 1;
}

.auth-brand {
  align-items: center;
  display: flex;
  gap: 12px;
}

.auth-brand__mark {
  align-items: center;
  background: #fff;
  border-radius: 10px;
  color: #101114;
  display: flex;
  font-size: 15px;
  font-weight: 800;
  height: 38px;
  justify-content: center;
  letter-spacing: 0;
  width: 38px;
}

.auth-brand__title {
  font-size: 15px;
  font-weight: 700;
}

.auth-brand__subtitle {
  color: rgba(255, 255, 255, 0.62);
  font-size: 12px;
}

.auth-brand__caption {
  color: rgba(255, 255, 255, 0.48);
  font-size: 11px;
  margin-top: 2px;
}

.auth-hero__content {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  max-width: 580px;
}

.auth-kicker {
  color: #7dd3fc;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  margin-bottom: 18px;
  text-transform: uppercase;
}

.auth-title {
  color: #fff;
  font-size: 52px;
  font-weight: 650;
  line-height: 1.02;
  margin: 0 0 20px;
}

.auth-copy {
  color: rgba(255, 255, 255, 0.72);
  font-size: 16px;
  line-height: 1.65;
  margin: 0 0 34px;
  max-width: 520px;
}

.auth-feature-list {
  display: grid;
  gap: 14px;
  margin-bottom: 34px;
}

.auth-feature {
  align-items: flex-start;
  display: flex;
  gap: 12px;
}

.auth-feature__icon {
  align-items: center;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #38bdf8;
  display: flex;
  flex: 0 0 auto;
  height: 36px;
  justify-content: center;
  width: 36px;
}

.auth-feature h2 {
  color: #fff;
  font-size: 14px;
  margin: 0 0 3px;
}

.auth-feature p {
  color: rgba(255, 255, 255, 0.58);
  font-size: 13px;
  line-height: 1.45;
  margin: 0;
}

.auth-metrics {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(3, 1fr);
  padding-top: 18px;
}

.auth-metrics span {
  display: block;
  font-size: 22px;
  font-weight: 800;
}

.auth-metrics p {
  color: rgba(255, 255, 255, 0.58);
  font-size: 12px;
  margin: 3px 0 0;
}

.auth-panel {
  align-items: center;
  display: flex;
  justify-content: center;
  padding: 40px;
}

.auth-card {
  background: var(--paper);
  border: 1px solid var(--border);
  border-radius: 18px;
  box-shadow: var(--shadow-lg);
  max-width: 420px;
  padding: 28px;
  width: 100%;
}

.auth-card__eyebrow {
  color: var(--accent-ink);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  margin-bottom: 8px;
  text-transform: uppercase;
}

.auth-card__header h2 {
  color: var(--ink);
  font-size: 30px;
  font-weight: 650;
  line-height: 1.1;
  margin: 0;
}

.auth-card__header p {
  color: var(--muted);
  font-size: 14px;
  line-height: 1.55;
  margin: 10px 0 22px;
}

.auth-tabs {
  background: var(--bg-sunken);
  border-radius: 10px;
  display: grid;
  gap: 4px;
  grid-template-columns: repeat(2, 1fr);
  margin-bottom: 18px;
  padding: 4px;
}

.auth-tabs__button {
  background: transparent;
  border: 0;
  border-radius: 7px;
  color: var(--muted);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  height: 34px;
}

.auth-tabs__button--active {
  background: var(--paper);
  box-shadow: var(--shadow-sm);
  color: var(--ink);
}

.auth-error {
  background: var(--ai-bg);
  border-radius: 10px;
  color: var(--ai-ink);
  font-size: 13px;
  margin-bottom: 14px;
  padding: 10px 12px;
}

.auth-form {
  display: grid;
  gap: 12px;
}

.auth-field {
  display: grid;
  gap: 6px;
}

.auth-field span {
  color: var(--ink-2);
  font-size: 12px;
  font-weight: 600;
}

.auth-field .va-input {
  height: 42px;
  width: 100%;
}

.auth-submit {
  height: 44px;
  justify-content: center;
  margin-top: 6px;
  width: 100%;
}

@media (max-width: 920px) {
  .auth-page {
    grid-template-columns: 1fr;
  }

  .auth-hero {
    min-height: auto;
    padding: 28px 22px 30px;
  }

  .auth-hero__content {
    margin-top: 42px;
  }

  .auth-title {
    font-size: 38px;
  }

  .auth-panel {
    padding: 22px;
  }
}

@media (max-width: 520px) {
  .auth-hero {
    padding: 22px 16px 24px;
  }

  .auth-title {
    font-size: 31px;
  }

  .auth-copy {
    font-size: 14px;
  }

  .auth-metrics {
    grid-template-columns: 1fr;
  }

  .auth-panel {
    padding: 16px;
  }

  .auth-card {
    border-radius: 14px;
    padding: 20px;
  }
}
</style>
