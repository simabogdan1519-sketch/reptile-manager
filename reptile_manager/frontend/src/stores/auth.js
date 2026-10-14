import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { auth as authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('access_token'))

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin    = computed(() => !!user.value?.is_admin)

  async function login(username, password) {
    const res = await authApi.login(username, password)
    token.value = res.data.access_token
    localStorage.setItem('access_token', token.value)
    await fetchMe()
  }

  async function fetchMe() {
    try {
      const res = await authApi.me()
      user.value = res.data
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
  }

  return { user, token, isLoggedIn, isAdmin, login, fetchMe, logout }
})
