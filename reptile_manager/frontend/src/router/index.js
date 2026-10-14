import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Hash history (#/) works regardless of what base path HA Ingress uses
const routes = [
  { path: '/login', component: () => import('@/views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    children: [
      { path: '',              redirect: '/dashboard' },
      { path: 'dashboard',    component: () => import('@/views/Dashboard.vue') },
      { path: 'animals',      component: () => import('@/views/AnimalList.vue') },
      { path: 'animals/new',  component: () => import('@/views/AnimalForm.vue') },
      { path: 'animals/:id',       component: () => import('@/views/AnimalDetail.vue') },
      { path: 'animals/:id/edit',  component: () => import('@/views/AnimalForm.vue') },
      { path: 'animals/:id/tree',  component: () => import('@/views/FamilyTree.vue') },
      { path: 'animals/:id/label', component: () => import('@/views/AnimalLabel.vue') },
      { path: 'feedings',  component: () => import('@/views/FeedingLog.vue') },
      { path: 'sheddings', component: () => import('@/views/SheddingLog.vue') },
      { path: 'breeding',  component: () => import('@/views/Breeding.vue') },
      { path: 'export',    component: () => import('@/views/Export.vue') },
      { path: 'settings',  component: () => import('@/views/Settings.vue') },
      { path: 'users',     component: () => import('@/views/UsersGroups.vue'), meta: { admin: true } },
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  if (to.meta.public) return true
  if (!authStore.isLoggedIn) return '/login'
  if (!authStore.user) await authStore.fetchMe()
  if (!authStore.isLoggedIn) return '/login'
  if (to.meta.admin && !authStore.isAdmin) return '/dashboard'
  return true
})

export default router
