<template>
  <div style="min-height:100vh;display:grid;grid-template-columns:1fr 1fr;background:var(--bg)">
    <!-- Left — brand panel -->
    <div style="padding:48px 56px;background:linear-gradient(180deg,#1F1D1A 0%,#2A2722 100%);color:#fff;display:flex;flex-direction:column">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:34px;height:34px;border-radius:8px;background:#fff;color:var(--ink);display:grid;place-items:center;font-family:var(--font-serif);font-size:22px;padding-top:2px">V</div>
        <div>
          <div style="font-size:15px;font-weight:600">Veritas</div>
          <div style="font-size:11px;opacity:.6">AI Text Integrity</div>
        </div>
      </div>

      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;max-width:460px">
        <div class="serif" style="font-size:44px;line-height:1.1;font-weight:400;letter-spacing:-0.01em;margin-bottom:20px">
          Доверие к цифровому контенту — в одном клике.
        </div>
        <div style="font-size:15px;opacity:.75;line-height:1.6;margin-bottom:32px">
          Посегментная разметка ИИ-генерации, проверка плагиата и пакетная обработка для учителей, рецензентов и QA-специалистов.
        </div>
        <div style="display:flex;flex-direction:column;gap:14px">
          <div v-for="f in features" :key="f.title" style="display:flex;gap:12px">
            <div style="width:32px;height:32px;border-radius:8px;background:rgba(255,255,255,.06);display:grid;place-items:center;flex-shrink:0">
              <VIcon :name="f.icon" :size="15" />
            </div>
            <div>
              <div style="font-size:14px;font-weight:500">{{ f.title }}</div>
              <div style="font-size:13px;opacity:.6">{{ f.sub }}</div>
            </div>
          </div>
        </div>
      </div>

      <div style="font-size:12px;opacity:.5">© 2026 Veritas — AI Text Integrity</div>
    </div>

    <!-- Right — form -->
    <div style="padding:48px 56px;display:flex;flex-direction:column;justify-content:center;align-items:center">
      <div style="width:100%;max-width:380px">
        <div class="serif" style="font-size:34px;font-weight:400;letter-spacing:-0.01em;margin-bottom:6px">
          {{ tab==='login' ? 'С возвращением' : 'Создать аккаунт' }}
        </div>
        <div style="font-size:14px;color:var(--muted);margin-bottom:28px">
          {{ tab==='login' ? 'Войдите, чтобы продолжить работу с анализами.' : 'Несколько полей — и вы начинаете.' }}
        </div>

        <!-- Tab toggle -->
        <div style="display:inline-flex;background:var(--bg-sunken);border-radius:8px;padding:3px;margin-bottom:18px">
          <button v-for="t in tabs" :key="t.id" @click="tab=t.id" :style="{
            padding:'6px 16px',border:'none',
            background: tab===t.id ? 'var(--paper)' : 'transparent',
            borderRadius:'5px',fontSize:'12px',fontWeight:500,
            color: tab===t.id ? 'var(--ink)' : 'var(--muted)',
            cursor:'pointer',boxShadow: tab===t.id ? 'var(--shadow-sm)' : 'none',
            fontFamily:'var(--font-sans)',
          }">{{ t.label }}</button>
        </div>

        <div v-if="errorMsg" style="margin-bottom:14px;padding:10px 14px;background:var(--ai-bg);border-radius:8px;font-size:13px;color:var(--ai-ink)">
          {{ errorMsg }}
        </div>

        <form @submit.prevent="submit" style="display:flex;flex-direction:column;gap:12px">
          <template v-if="tab==='register'">
            <FormField label="Имя">
              <input class="va-input" v-model="form.first_name" placeholder="Анна" style="width:100%;height:42px" required />
            </FormField>
            <FormField label="Фамилия">
              <input class="va-input" v-model="form.last_name" placeholder="Петрова" style="width:100%;height:42px" required />
            </FormField>
          </template>
          <FormField label="Почта">
            <input class="va-input" v-model="form.email" type="email" placeholder="anna@school.ru" style="width:100%;height:42px" required />
          </FormField>
          <FormField label="Пароль">
            <input class="va-input" v-model="form.password" type="password" placeholder="••••••••" style="width:100%;height:42px" required minlength="6" />
          </FormField>
          <template v-if="tab==='register'">
            <FormField label="Роль">
              <select class="va-input" v-model="form.role" style="width:100%;height:42px">
                <option value="student">Студент</option>
                <option value="teacher">Преподаватель</option>
              </select>
            </FormField>
          </template>

          <button type="submit" class="va-btn accent" style="height:44px;justify-content:center;margin-top:6px" :disabled="isLoading">
            <span v-if="isLoading" class="va-spinner" />
            {{ tab==='login' ? 'Войти в Veritas' : 'Создать аккаунт' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, defineComponent, h } from 'vue'
import { useRouter } from 'vue-router'
import { AuthService, defaultRouteForRole } from '../services/auth'
import VIcon from '../components/VIcon.vue'

const FormField = defineComponent({
  props: ['label', 'hint'],
  setup(p, { slots }) {
    return () => h('label', { style: 'display:flex;flex-direction:column;gap:6px' }, [
      h('div', { style: 'display:flex;justify-content:space-between;font-size:12px;color:var(--muted)' }, [
        h('span', { style: 'font-weight:500;color:var(--ink-2)' }, p.label),
        p.hint ? h('a', { href: '#', onClick: (e: Event) => e.preventDefault(), style: 'color:var(--accent-ink);text-decoration:none' }, p.hint) : null,
      ]),
      slots.default?.(),
    ])
  },
})

const router = useRouter()
const tab = ref<'login'|'register'>('login')
const isLoading = ref(false)
const errorMsg = ref('')

const tabs = [{ id: 'login', label: 'Войти' }, { id: 'register', label: 'Регистрация' }]
const features = [
  { icon: 'sparkle', title: 'Объяснимые результаты', sub: 'Видно, какие предложения написала машина, а какие — человек.' },
  { icon: 'shield', title: 'Проверка плагиата', sub: 'Научные базы, веб, архив студенческих работ.' },
  { icon: 'layers', title: 'Пакетный режим', sub: 'До 50 документов параллельно.' },
]

const form = reactive({ email: '', password: '', first_name: '', last_name: '', role: 'student' as 'student'|'teacher' })

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
      await AuthService.register({ email: form.email, password: form.password, first_name: form.first_name, last_name: form.last_name, role: form.role })
    }
    router.push(defaultRouteForRole(AuthService.getUser()?.role))
  } catch (e: any) {
    errorMsg.value = e.error || 'Ошибка. Проверьте данные.'
  } finally {
    isLoading.value = false
  }
}
</script>
