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
      path: '/report',
      name: 'report',
      component: () => import('@/views/ReportView.vue'),
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
    },
    {
      path: '/push',
      name: 'push',
      component: () => import('@/views/PushSettings.vue'),
    },
    {
      path: '/achievements',
      name: 'achievements',
      component: () => import('@/views/AchievementsView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
    },
    {
      path: '/mall-admin',
      name: 'mall-admin',
      component: () => import('@/views/MallAdminView.vue'),
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
          component: () => import('@/views/CalendarView.vue'),
        },
        {
          path: 'calendar/day/:date',
          name: 'calendar-day',
          component: () => import('@/views/DayDetailView.vue'),
        },
        {
          path: 'body',
          name: 'body',
          component: () => import('@/views/BodyMetricsView.vue'),
        },
        {
          path: 'journal',
          redirect: '/calendar',
        },
        {
          path: 'points-mall',
          name: 'points-mall',
          component: () => import('@/views/PointsMallView.vue'),
        },
        {
          path: 'goals',
          redirect: '/points-mall',
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
