<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/i18n'
import { dashboard } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { fmtRelative, foodLabel, sexNotation, sexBadge } from '@/utils/format'
import { languages, locale } from '@/i18n'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import AnimalAvatar from '@/components/AnimalAvatar.vue'
import EmptyState from '@/components/EmptyState.vue'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const stats = ref(null)
const loading = ref(true)

onMounted(async () => {
  try { stats.value = (await dashboard.stats()).data }
  finally { loading.value = false }
})

const today = computed(() => new Date().toLocaleDateString(languages[locale.value].intl,
  { weekday: 'long', day: 'numeric', month: 'long' }))

const greeting = computed(() => {
  const h = new Date().getHours()
  const k = h < 5 ? 'evening' : h < 12 ? 'morning' : h < 18 ? 'afternoon' : 'evening'
  return t(`dashboard.greet_${k}`, { name: auth.user?.username || '' })
})

const due = computed(() => [...(stats.value?.animals_needing_feeding || [])]
  .sort((a, b) => (b.days_since_feeding ?? 9999) - (a.days_since_feeding ?? 9999)))

const activity = computed(() => {
  if (!stats.value) return []
  const f = stats.value.recent_feedings.map(x => ({ ...x, kind: 'feeding' }))
  const s = stats.value.recent_sheddings.map(x => ({ ...x, kind: 'shed' }))
  return [...f, ...s].sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 10)
})

function open(tile) {
  if (tile.to) router.push(tile.to)
  else document.getElementById('due')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function pct(a) {
  if (a.days_since_feeding == null) return 100
  return Math.min(100, Math.round((a.days_since_feeding / (a.threshold_days || 1)) * 100))
}

const tiles = computed(() => !stats.value ? [] : [
  { key: 'active_animals',  value: stats.value.active_animals,       icon: 'reptile', to: '/animals' },
  { key: 'feedings_month',  value: stats.value.feedings_this_month,  icon: 'feeding', to: '/feedings' },
  { key: 'sheddings_month', value: stats.value.sheddings_this_month, icon: 'shed',    to: '/sheddings' },
  { key: 'not_fed',         value: stats.value.animals_not_fed_7days, icon: 'bell',   to: null, warn: stats.value.animals_not_fed_7days > 0 },
])
</script>

<template>
  <div>
    <PageHeader :eyebrow="today" :title="greeting" :subtitle="t('dashboard.subtitle')">
      <template #actions>
        <button class="btn-secondary" @click="router.push('/feedings?new=1')"><Icon name="feeding" :size="16" />{{ t('feeding.add') }}</button>
        <button class="btn-primary" @click="router.push('/animals/new')"><Icon name="plus" :size="16" />{{ t('animal.add') }}</button>
      </template>
    </PageHeader>

    <div v-if="loading" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="i in 4" :key="i" class="card h-[118px] animate-pulse" />
    </div>

    <template v-else-if="stats">
      <!-- KPI tiles -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6 stagger">
        <button v-for="tile in tiles" :key="tile.key" type="button"
                class="card text-left group transition-all hover:-translate-y-0.5"
                :class="tile.warn ? '!border-heat-400/40 !bg-heat-400/[0.06]' : 'hover:border-line-strong'"
                @click="open(tile)">
          <div class="flex items-center justify-between">
            <span class="eyebrow" :class="tile.warn ? '!text-heat-400' : ''">{{ t('dashboard.' + tile.key) }}</span>
            <span class="w-8 h-8 rounded-lg grid place-items-center transition-colors"
                  :class="tile.warn ? 'bg-heat-400/15 text-heat-400' : 'bg-ink-800 text-fg-faint group-hover:text-moss-400'">
              <Icon :name="tile.icon" :size="16" />
            </span>
          </div>
          <div class="mt-4 font-display text-[40px] leading-none font-semibold num"
               :class="tile.warn ? 'text-heat-400' : 'text-fg'">{{ tile.value }}</div>
        </button>
      </div>

      <div class="grid lg:grid-cols-[1.45fr_1fr] gap-4 items-start stagger">
        <!-- Feeding due -->
        <section id="due" class="panel">
          <div class="panel-head">
            <div class="flex items-center gap-2.5">
              <span class="w-2 h-2 rounded-full" :class="due.length ? 'bg-heat-400 shadow-[0_0_10px_rgb(var(--heat-400))]' : 'bg-moss-400'" />
              <h2 class="panel-title">{{ t('dashboard.feeding_modal_title') }}</h2>
              <span v-if="due.length" class="badge-yellow num">{{ due.length }}</span>
            </div>
            <button class="link" @click="router.push('/feedings')">{{ t('dashboard.to_feedings') }} <Icon name="chevron" :size="14" /></button>
          </div>

          <EmptyState v-if="!due.length" icon="check" :title="t('dashboard.all_fed')" :text="t('dashboard.all_fed_text')" />

          <ul v-else class="divide-y divide-line/70">
            <li v-for="a in due" :key="a.id"
                class="flex items-center gap-3.5 px-5 py-3.5 cursor-pointer hover:bg-ink-850/70 transition-colors"
                @click="router.push(`/animals/${a.id}`)">
              <AnimalAvatar :animal="a" />
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-semibold text-fg truncate">{{ a.name }}</span>
                  <span :class="sexBadge(a.sex)">{{ sexNotation(a.sex) }}</span>
                </div>
                <p class="text-xs text-fg-faint italic truncate mt-0.5">{{ a.species }}<span v-if="a.morph" class="not-italic text-moss-400/80"> · {{ a.morph }}</span></p>
                <div class="mt-2 h-1 rounded-full bg-ink-800 overflow-hidden">
                  <div class="h-full rounded-full bg-gradient-to-r from-heat-500 to-coral-400" :style="{ width: pct(a) + '%' }" />
                </div>
              </div>
              <div class="text-right flex-shrink-0 w-20">
                <div class="font-display text-[22px] font-semibold num text-heat-400 leading-none">
                  {{ a.days_since_feeding ?? '—' }}<span class="text-sm text-fg-faint ml-0.5">{{ a.days_since_feeding != null ? t('common.d') : '' }}</span>
                </div>
                <div class="text-[11px] text-fg-faint mt-1">{{ a.days_since_feeding == null ? t('dashboard.never_fed') : t('dashboard.threshold_n', { n: a.threshold_days }) }}</div>
              </div>
            </li>
          </ul>
        </section>

        <!-- Activity -->
        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">{{ t('dashboard.activity') }}</h2>
            <Icon name="activity" :size="16" class="text-fg-faint" />
          </div>
          <EmptyState v-if="!activity.length" icon="activity" :title="t('dashboard.no_activity')" />
          <ol v-else class="px-5 py-4 relative">
            <li v-for="(e, i) in activity" :key="e.kind + e.id" class="relative pl-9 pb-4 last:pb-0">
              <span v-if="i < activity.length - 1" class="absolute left-[13px] top-7 bottom-0 w-px bg-line" />
              <span class="absolute left-0 top-0.5 w-[27px] h-[27px] rounded-lg grid place-items-center border"
                    :class="e.kind === 'feeding'
                      ? (e.accepted ? 'bg-moss-400/10 border-moss-400/25 text-moss-400' : 'bg-coral-500/10 border-coral-500/25 text-coral-400')
                      : 'bg-lagoon-400/10 border-lagoon-400/25 text-lagoon-400'">
                <Icon :name="e.kind === 'feeding' ? 'feeding' : 'shed'" :size="14" />
              </span>
              <div class="flex items-baseline justify-between gap-3">
                <p class="text-[13.5px] text-fg truncate">
                  <span class="font-semibold">{{ e.animal_name }}</span>
                  <span class="text-fg-muted">
                    <template v-if="e.kind === 'feeding'"> · {{ foodLabel(e) }}</template>
                    <template v-else> · {{ e.complete ? t('shedding.complete_label') : t('shedding.incomplete_label') }}</template>
                  </span>
                </p>
                <span class="text-[11.5px] text-fg-faint whitespace-nowrap">{{ fmtRelative(e.date) }}</span>
              </div>
              <p v-if="e.kind === 'feeding' && !e.accepted" class="text-xs text-coral-400 mt-0.5">{{ t('feeding.rejected_label') }}</p>
            </li>
          </ol>
        </section>
      </div>
    </template>
  </div>
</template>
