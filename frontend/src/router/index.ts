import { createRouter, createWebHistory } from 'vue-router'
import TabLayout from '@/layouts/TabLayout.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/workout',
      name: 'workout',
      component: () => import('@/views/WorkoutView.vue'),
    },
    {
      path: '/',
      component: TabLayout,
      redirect: '/today',
      children: [
        {
          path: 'today',
          name: 'today',
          component: () => import('@/views/TodayView.vue'),
        },
        {
          path: 'calendar',
          name: 'calendar',
          component: () => import('@/views/PlaceholderTabView.vue'),
          props: { phase: 'P1', title: '日历' },
        },
        {
          path: 'journal',
          name: 'journal',
          component: () => import('@/views/PlaceholderTabView.vue'),
          props: { phase: 'P1', title: '日志' },
        },
        {
          path: 'goals',
          name: 'goals',
          component: () => import('@/views/PlaceholderTabView.vue'),
          props: { phase: 'P2', title: '目标' },
        },
        {
          path: 'mine',
          name: 'mine',
          component: () => import('@/views/MineView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (to.name === 'login' && auth.isAuthenticated) {
      return { name: 'today' }
    }
    return true
  }
  if (!auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
