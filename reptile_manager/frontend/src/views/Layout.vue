<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n, setLocale, languages } from '@/i18n'
import Icon from '@/components/Icon.vue'
import Brand from '@/components/Brand.vue'
import { canInstall, promptInstall, online } from '@/utils/pwa'

const router = useRouter()
const route  = useRoute()
const auth   = useAuthStore()
const { t, locale } = useI18n()

const drawer   = ref(false)
const quick    = ref(false)
const isMobile = ref(false)

function checkMobile() { isMobile.value = window.innerWidth < 1024 }
onMounted(() => { checkMobile(); window.addEventListener('resize', checkMobile) })
onUnmounted(() => window.removeEventListener('resize', checkMobile))
router.afterEach(() => { drawer.value = false; quick.value = false })

const tabs = [
  { to: '/dashboard', icon: 'dashboard', key: 'nav.dashboard' },
  { to: '/animals',   icon: 'reptile',   key: 'nav.animals' },
  null,
  { to: '/feedings',  icon: 'feeding',   key: 'nav.feedings' },
]
const quickActions = [
  { to: '/feedings?new=1', icon: 'feeding', key: 'feeding.add' },
  { to: '/sheddings?new=1', icon: 'shed', key: 'shedding.add' },
  { to: '/animals/new', icon: 'reptile', key: 'animal.add' },
  { to: '/breeding?new=1', icon: 'egg', key: 'breeding.add' },
]

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
    <header class="lg:hidden sticky top-0 z-30 flex items-center gap-3 px-4 h-14 border-b border-line bg-ink-950/85 backdrop-blur-md"
            style="padding-top: env(safe-area-inset-top); height: calc(3.5rem + env(safe-area-inset-top))">
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
        <button v-if="canInstall" class="btn-secondary w-full" @click="promptInstall">
          <Icon name="download" :size="16" />{{ t('pwa.install') }}
        </button>
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
      <div v-if="!online" class="sticky top-14 lg:top-0 z-20 bg-heat-400/15 border-b border-heat-400/30 text-heat-400 text-[13px] px-4 py-2 flex items-center gap-2 backdrop-blur">
        <Icon name="alert" :size="15" />{{ t('pwa.offline') }}
      </div>
      <div class="mx-auto w-full max-w-[1240px] px-4 sm:px-6 lg:px-10 py-6 lg:py-10 pb-28 lg:pb-10">
        <RouterView v-slot="{ Component }">
          <component :is="Component" :key="route.fullPath" />
        </RouterView>
      </div>
    </main>

    <!-- Mobile tab bar -->
    <nav class="lg:hidden fixed bottom-0 inset-x-0 z-30 border-t border-line bg-ink-950/90 backdrop-blur-xl"
         style="padding-bottom: env(safe-area-inset-bottom)">
      <div class="grid grid-cols-5 h-16">
        <template v-for="(tab, i) in tabs" :key="i">
          <RouterLink v-if="tab" :to="tab.to" class="tabbar-item" :class="{ on: route.path.startsWith(tab.to) }">
            <Icon :name="tab.icon" :size="21" /><span>{{ t(tab.key) }}</span>
          </RouterLink>
          <div v-else class="grid place-items-center">
            <button class="w-12 h-12 -mt-5 rounded-2xl bg-moss-400 text-moss-ink grid place-items-center shadow-glow active:scale-95 transition-transform"
                    :aria-label="t('common.add')" @click="quick = !quick">
              <Icon :name="quick ? 'x' : 'plus'" :size="22" :stroke="2.4" />
            </button>
          </div>
        </template>
        <button class="tabbar-item" @click="drawer = true"><Icon name="menu" :size="21" /><span>{{ t('nav.more') }}</span></button>
      </div>
    </nav>

    <!-- Quick add sheet -->
    <Transition name="fade">
      <div v-if="quick" class="lg:hidden fixed inset-0 z-20 bg-black/60 backdrop-blur-sm" @click="quick = false" />
    </Transition>
    <Transition name="sheet">
      <div v-if="quick" class="lg:hidden fixed inset-x-3 z-30 rounded-2xl bg-ink-900 shadow-pop p-2 grid grid-cols-2 gap-2"
           style="bottom: calc(5rem + env(safe-area-inset-bottom))">
        <RouterLink v-for="a in quickActions" :key="a.to" :to="a.to"
                    class="flex flex-col items-start gap-2 rounded-xl border border-line bg-ink-850 p-3.5 active:bg-ink-800">
          <span class="w-9 h-9 rounded-lg bg-moss-400/10 text-moss-400 grid place-items-center"><Icon :name="a.icon" :size="18" /></span>
          <span class="text-[13.5px] font-semibold text-fg">{{ t(a.key) }}</span>
        </RouterLink>
      </div>
    </Transition>
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
.sheet-enter-active, .sheet-leave-active { transition: transform .25s cubic-bezier(.2,.7,.2,1), opacity .2s; }
.sheet-enter-from, .sheet-leave-to { transform: translateY(16px); opacity: 0; }
.tabbar-item { @apply flex flex-col items-center justify-center gap-1 text-[10.5px] font-semibold text-fg-faint transition-colors; }
.tabbar-item.on { @apply text-moss-400; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
