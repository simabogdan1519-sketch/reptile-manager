<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n, setLocale, languages } from '@/i18n'


const router = useRouter()
const auth   = useAuthStore()
const { t, locale } = useI18n()

const sidebarOpen = ref(false)
const isMobile    = ref(false)
const showLangMenu = ref(false)

function checkMobile() {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) sidebarOpen.value = true
}
onMounted(() => { checkMobile(); window.addEventListener('resize', checkMobile) })
onUnmounted(() => window.removeEventListener('resize', checkMobile))
router.afterEach(() => { if (isMobile.value) sidebarOpen.value = false })

const baseNavItems = [
  { to: '/dashboard', icon: '📊', key: 'nav.dashboard' },
  { to: '/animals',   icon: '🦎', key: 'nav.animals' },
  { to: '/feedings',  icon: '🍖', key: 'nav.feedings' },
  { to: '/sheddings', icon: '🐚', key: 'nav.sheddings' },
  { to: '/breeding',  icon: '🥚', key: 'nav.breeding' },
  { to: '/export',    icon: '📜', key: 'nav.herkunftsnachweis' },
  { to: '/settings',  icon: '⚙️', key: 'nav.settings' },
]
const navItems = computed(() => auth.isAdmin
  ? [...baseNavItems.slice(0, -1), { to: '/users', icon: '👥', key: 'access.nav' }, baseNavItems.at(-1)]
  : baseNavItems)

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Mobile overlay -->
    <Transition name="fade">
      <div v-if="isMobile && sidebarOpen"
           class="fixed inset-0 bg-black/60 z-10"
           @click="sidebarOpen = false" />
    </Transition>

    <!-- Sidebar -->
    <aside :class="[
      'flex-shrink-0 bg-surface-800 border-r border-surface-600 flex flex-col transition-all duration-200 z-20',
      isMobile
        ? 'fixed h-full ' + (sidebarOpen ? 'translate-x-0 w-56' : '-translate-x-full w-56')
        : (sidebarOpen ? 'w-56' : 'w-16')
    ]">
      <div class="flex items-center gap-3 px-4 py-5 border-b border-surface-600 flex-shrink-0">
        <span class="text-2xl">🦎</span>
        <span v-if="sidebarOpen" class="font-bold text-brand-400 text-base leading-tight">
          Reptile<br>Manager
        </span>
      </div>

      <nav class="flex-1 py-4 overflow-y-auto">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to"
          class="flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg text-slate-400
                 hover:text-slate-200 hover:bg-surface-600 transition-colors"
          active-class="!text-brand-400 !bg-surface-600">
          <span class="text-lg w-6 text-center flex-shrink-0">{{ item.icon }}</span>
          <span v-if="sidebarOpen" class="text-sm font-medium truncate">{{ t(item.key) }}</span>
        </RouterLink>
      </nav>

      <div class="border-t border-surface-600 p-3 flex-shrink-0 space-y-2">
        <!-- Language selector -->
        <div v-if="sidebarOpen" class="relative">
          <button @click="showLangMenu = !showLangMenu"
                  class="w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs
                         text-slate-500 hover:text-slate-300 hover:bg-surface-600 transition-colors">
            🌐 {{ languages[locale]?.name ?? locale }}
            <span class="ml-auto opacity-50">▾</span>
          </button>
          <div v-if="showLangMenu"
               class="absolute bottom-full left-0 right-0 mb-1 bg-surface-600 rounded-lg
                      border border-surface-500 shadow-xl overflow-hidden z-30">
            <button v-for="(lang, code) in languages" :key="code"
                    @click="setLocale(code); showLangMenu = false"
                    class="w-full flex items-center gap-2 px-3 py-2 text-xs text-left
                           hover:bg-surface-500 transition-colors"
                    :class="locale === code ? 'text-brand-400' : 'text-slate-300'">
              <span>{{ lang.flag }}</span>
              <span>{{ lang.name }}</span>
              <span v-if="locale === code" class="ml-auto">✓</span>
            </button>
          </div>
        </div>
        <!-- User -->
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center
                      text-sm font-bold text-white flex-shrink-0">
            {{ auth.user?.username?.[0]?.toUpperCase() ?? '?' }}
          </div>
          <div v-if="sidebarOpen" class="flex-1 min-w-0">
            <p class="text-sm font-medium text-slate-200 truncate">{{ auth.user?.username }}</p>
            <button @click="logout" class="text-xs text-slate-500 hover:text-red-400 transition-colors">
              {{ t('nav.logout') }}
            </button>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main -->
    <div class="flex-1 flex flex-col overflow-hidden min-w-0">
      <header class="bg-surface-800 border-b border-surface-600 px-4 py-3
                     flex items-center gap-4 flex-shrink-0">
        <button @click="sidebarOpen = !sidebarOpen"
                class="text-slate-400 hover:text-slate-200 transition-colors text-xl w-8 text-center">☰</button>
        <span class="text-sm text-slate-500 md:hidden">Reptile Manager</span>
      </header>
      <main class="flex-1 overflow-y-auto p-4 md:p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
