import { createRouter, createWebHistory } from 'vue-router'
import { AuthService } from '../services/auth'
import HomePage from '../views/HomePage.vue'
import DetectorPage from '../views/DetectorPage.vue'
import HistoryPage from '../views/HistoryPage.vue'
import PlagiarismPage from '../views/PlagiarismPage.vue'
import AnalysisDetailPage from '../views/AnalysisDetailPage.vue'
import BatchUploadPage from '../views/BatchUploadPage.vue'
import AuthPage from '../views/AuthPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/auth',
      name: 'auth',
      component: AuthPage,
      meta: { requiresGuest: true },
    },
    {
      path: '/',
      name: 'home',
      component: HomePage,
      meta: { requiresAuth: true },
    },
    {
      path: '/detector',
      name: 'detector',
      component: DetectorPage,
      meta: { requiresAuth: true, requiresRole: 'developer' },
    },
    {
      path: '/history',
      name: 'history',
      component: HistoryPage,
      meta: { requiresAuth: true },
    },
    {
      path: '/analysis/:id',
      name: 'analysis-detail',
      component: AnalysisDetailPage,
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: '/batch',
      name: 'multiple-analysis',
      component: BatchUploadPage,
      meta: { requiresAuth: true },
    },
    {
      path: '/plagiarism',
      name: 'plagiarism',
      component: PlagiarismPage,
      meta: { requiresAuth: true },
    },
    {
      path: '/plagiarism/:id',
      name: 'plagiarism-detail',
      component: () => import('../views/PlagiarismDetailPage.vue'),
      props: true,
      meta: { requiresAuth: true },
    },
  ],
})

// Глобальный навигационный guard
router.beforeEach((to, from, next) => {
  const isAuthenticated = AuthService.isAuthenticated()
  const requiresRole = to.meta?.requiresRole as string | undefined
  const hasRole = requiresRole ? AuthService.hasRole(requiresRole) : true

  // Если маршрут требует авторизации, но пользователь не авторизован
  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: 'auth' })
    return
  }

  // Если маршрут требует конкретную роль и она отсутствует
  if (to.meta.requiresAuth && requiresRole && !hasRole) {
    next({ name: 'home' })
    return
  }

  // Если маршрут только для гостей, но пользователь авторизован
  if (to.meta.requiresGuest && isAuthenticated) {
    next({ name: 'home' })
    return
  }

  next()
})

export default router
