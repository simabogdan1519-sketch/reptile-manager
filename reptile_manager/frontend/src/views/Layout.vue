<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n, setLocale, languages } from '@/i18n'
import Icon from '@/components/Icon.vue'
import Brand from '@/components/Brand.vue'

const router = useRouter()
const route  = useRoute()
const auth   = useAuthStore()
const { t, locale } = useI18n()

const drawer   = ref(false)
const isMobile = ref(false)

function checkMobile() { isMobile.value = window.innerWidth < 1024 }
onMounted(() => { checkMobile(); window.addEventListener('resize', checkMobile) })
onUnmounted(() => window.removeEventListener('resize', checkMobile))
router.afterEach(() => { drawer.value = false })

const sections = computed(() => {
  const main = [
    { to: '/dashboard', icon: 'dashboard',   key: 'nav.dashboard' },
    { to: '/animals',   icon: 'reptile',     key: 'nav.animals' },
    { to: '/feedings',  icon: 'feeding',     key: 'nav.feedings' },
    { to: '/sheddings', icon: 'shed',        key: 'nav.sheddings' },
    { to: '/breeding',  icon: 'egg',         key: 'nav.breeding' },
  ]
  const tools = [
    { to: '/export',    icon: 'certificate', key: 'nav.herkunftsnachweis' },
  ]
  const system = [
    ...(auth.isAdmin ? [{ to: '/users', icon: 'users', key: 'access.nav' }] : []),
    { to: '/settings',  icon: 'settings',    key: 'nav.settings' },
  ]
  return [
    { label: 'nav.section_husbandry', items: main },
    { label: 'nav.section_documents', items: tools },
    { label: 'nav.section_system',    items: system },
  ]
})

const allItems = computed(() => sections.value.flatMap(s => s.items))
const currentTitle = computed(() => {
  const hit = allItems.value.find(i => route.path.startsWith(i.to))
  return hit ? t(hit.key) : 'Reptile Manager'
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen lg:flex">
    <!-- Mobile top bar -->
    <header class="lg:hidden sticky top-0 z-30 flex items-center gap-3 px-4 h-14 border-b border-line bg-ink-950/85 backdrop-blur-md">
      <button class="icon-btn -ml-1" @click="drawer = true" aria-label="Menu"><Icon name="menu" :size="20" /></button>
      <Brand :size="26" />
      <span class="font-display font-semibold text-fg truncate">{{ currentTitle }}</span>
    </header>

    <!-- Drawer backdrop -->
    <Transition name="fade">
      <div v-if="isMobile && drawer" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-40" @click="drawer = false" />
    </Transition>

    <!-- Sidebar -->
    <aside
      class="fixed lg:sticky top-0 left-0 z-50 h-screen w-[264px] flex-shrink-0 flex flex-col
             border-r border-line bg-ink-900/95 lg:bg-ink-900/70 backdrop-blur-xl transition-transform duration-300"
      :class="isMobile ? (drawer ? 'translate-x-0 shadow-pop' : '-translate-x-full') : ''">

      <div class="flex items-center gap-3 px-5 h-[72px] border-b border-line flex-shrink-0">
        <Brand :size="34" />
        <div class="leading-tight min-w-0">
          <div class="font-display font-bold text-[16px] text-fg tracking-tight">Reptile Manager</div>
          <div class="eyebrow !text-[9.5px] mt-0.5">{{ t('nav.tagline') }}</div>
        </div>
        <button v-if="isMobile" class="icon-btn ml-auto" @click="drawer = false"><Icon name="x" /></button>
      </div>

      <nav class="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        <div v-for="sec in sections" :key="sec.label">
          <p class="eyebrow px-3 mb-2">{{ t(sec.label) }}</p>
          <div class="space-y-0.5">
            <RouterLink v-for="item in sec.items" :key="item.to" :to="item.to" custom v-slot="{ href, navigate, isActive }">
              <a :href="href" @click="navigate"
                 class="nav-item group"
                 :class="(isActive || route.path.startsWith(item.to)) ? 'nav-item-on' : ''">
                <Icon :name="item.icon" :size="18" class="nav-icon" />
                <span class="truncate">{{ t(item.key) }}</span>
              </a>
            </RouterLink>
          </div>
        </div>
      </nav>

      <div class="p-3 border-t border-line flex-shrink-0 space-y-3">
        <div class="flex items-center justify-between px-2">
          <span class="eyebrow">{{ t('settings.language') }}</span>
          <div class="seg">
            <button v-for="(lang, code) in languages" :key="code" :class="{ on: locale === code }"
                    @click="setLocale(code)">{{ lang.short }}</button>
          </div>
        </div>
        <div class="flex items-center gap-3 rounded-xl border border-line bg-ink-850/70 p-2.5">
          <div class="w-9 h-9 rounded-lg bg-moss-400 text-moss-ink grid place-items-center font-display font-bold text-sm flex-shrink-0">
            {{ auth.user?.username?.[0]?.toUpperCase() ?? '?' }}
          </div>
          <div class="flex-1 min-w-0 leading-tight">
            <p class="text-[13.5px] font-semibold text-fg truncate">{{ auth.user?.username }}</p>
            <p class="text-[11.5px] text-fg-faint truncate">
              {{ auth.isAdmin ? t('access.admin') : (auth.user?.groups?.map(g => g.name).join(', ') || t('access.member')) }}
            </p>
          </div>
          <button class="icon-btn danger" :title="t('nav.logout')" @click="logout"><Icon name="logout" :size="17" /></button>
        </div>
      </div>
    </aside>

    <!-- Main -->
    <main class="flex-1 min-w-0">
      <div class="mx-auto w-full max-w-[1240px] px-4 sm:px-6 lg:px-10 py-6 lg:py-10">
        <RouterView v-slot="{ Component }">
          <component :is="Component" :key="route.fullPath" />
        </RouterView>
      </div>
    </main>
  </div>
</template>

<style scoped>
.nav-item {
  @apply relative flex items-center gap-3 h-10 px-3 rounded-lg text-[14px] font-medium text-fg-muted
         transition-colors hover:text-fg hover:bg-ink-800/70;
}
.nav-icon { @apply text-fg-faint transition-colors; }
.nav-item:hover .nav-icon { @apply text-fg-muted; }
.nav-item-on { @apply text-fg bg-ink-800; box-shadow: inset 0 0 0 1px rgb(var(--line-strong)); }
.nav-item-on .nav-icon { @apply text-moss-400; }
.nav-item-on::before {
  content: ""; @apply absolute -left-3 top-2 bottom-2 w-[3px] rounded-r-full bg-moss-400;
  box-shadow: 0 0 12px rgb(var(--moss-400) / .7);
}
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
