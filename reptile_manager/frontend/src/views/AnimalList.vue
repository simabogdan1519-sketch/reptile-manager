<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/i18n'
import { animals as animalsApi, groups as groupsApi } from '@/api'
import { mediaUrl } from '@/utils/media'
import { sexNotation, sexBadge, ageParts } from '@/utils/format'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import EmptyState from '@/components/EmptyState.vue'

const { t } = useI18n()
const router = useRouter()

const list = ref([])
const search = ref('')
const scope = ref('active')          // 'active' | 'all'
const loading = ref(true)
const groupList = ref([])
const groupFilter = ref('all')       // 'all' | 'none' | <id>

let timer
async function load() {
  loading.value = true
  try {
    list.value = (await animalsApi.list({
      search: search.value || undefined,
      active_only: scope.value === 'active',
      limit: 500,
    })).data
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  load()
  try { groupList.value = (await groupsApi.list()).data } catch { /* non-critical */ }
})
watch(scope, load)
watch(search, () => { clearTimeout(timer); timer = setTimeout(load, 250) })

const filtered = computed(() => {
  if (groupFilter.value === 'all')  return list.value
  if (groupFilter.value === 'none') return list.value.filter(a => !a.group_id)
  return list.value.filter(a => a.group_id === groupFilter.value)
})
const hasUnassigned = computed(() => list.value.some(a => !a.group_id))
const showGroupFilter = computed(() => groupList.value.length > 1 || (groupList.value.length && hasUnassigned.value))

const counts = computed(() => ({
  male:    filtered.value.filter(a => a.sex === 'male').length,
  female:  filtered.value.filter(a => a.sex === 'female').length,
  unknown: filtered.value.filter(a => a.sex !== 'male' && a.sex !== 'female').length,
}))

function ageText(a) {
  const p = ageParts(a.date_of_birth)
  return p ? t(`common.age_${p.unit}`, { n: p.value }) : null
}
</script>

<template>
  <div>
    <PageHeader :eyebrow="t('animal.eyebrow')" :title="t('animal.title')">
      <template #subtitle>
        <span class="num">{{ counts.male }}.{{ counts.female }}.{{ counts.unknown }}</span>
        <span class="text-fg-faint"> · {{ t('animal.count', { n: filtered.length }) }}</span>
      </template>
      <template #actions>
        <button class="btn-primary" @click="router.push('/animals/new')"><Icon name="plus" :size="16" />{{ t('animal.add') }}</button>
      </template>
    </PageHeader>

    <!-- Toolbar -->
    <div class="flex flex-col sm:flex-row gap-2.5 mb-5">
      <div class="relative flex-1">
        <Icon name="search" :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-fg-faint pointer-events-none" />
        <input v-model="search" type="search" :placeholder="t('animal.search_placeholder')" class="!pl-9 h-10" />
      </div>
      <select v-if="showGroupFilter" v-model="groupFilter" class="sm:w-52 h-10">
        <option value="all">{{ t('access.all_groups') }}</option>
        <option v-for="g in groupList" :key="g.id" :value="g.id">{{ g.name }}</option>
        <option v-if="hasUnassigned" value="none">{{ t('access.unassigned') }}</option>
      </select>
      <div class="seg h-10 items-center self-start sm:self-auto">
        <button :class="{ on: scope === 'active' }" @click="scope = 'active'">{{ t('status.active') }}</button>
        <button :class="{ on: scope === 'all' }" @click="scope = 'all'">{{ t('common.all') }}</button>
      </div>
    </div>

    <div v-if="loading && !list.length" class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
      <div v-for="i in 8" :key="i" class="card p-0 h-[280px] animate-pulse" />
    </div>

    <div v-else-if="!filtered.length" class="card">
      <EmptyState :title="t('animal.noAnimals')" :text="search ? t('animal.no_match') : t('animal.empty_text')">
        <button v-if="!search" class="btn-primary" @click="router.push('/animals/new')"><Icon name="plus" :size="16" />{{ t('animal.add') }}</button>
      </EmptyState>
    </div>

    <div v-else class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-4 stagger">
      <article v-for="a in filtered" :key="a.id"
        class="group relative rounded-2xl border border-line bg-ink-900 overflow-hidden cursor-pointer shadow-panel
               transition-all duration-200 hover:-translate-y-1 hover:border-moss-400/40 hover:shadow-glow"
        @click="router.push(`/animals/${a.id}`)">
        <div class="relative aspect-[4/3] bg-ink-850 overflow-hidden">
          <img v-if="a.photo_url" :src="mediaUrl(a.photo_url)" :alt="a.name"
               class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.04]" />
          <div v-else class="absolute inset-0 grid place-items-center">
            <Icon name="reptile" :size="54" :stroke="1.2" class="text-line-strong" />
          </div>
          <div class="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-ink-900 to-transparent" />
          <div class="absolute top-2.5 left-2.5 right-2.5 flex items-start justify-between gap-2">
            <span v-if="a.tracking_id" class="badge-gray !bg-ink-950/75 backdrop-blur num">#{{ a.tracking_id }}</span>
            <span v-if="a.status && a.status !== 'active'" class="badge ml-auto backdrop-blur"
                  :class="a.status === 'sold' ? 'bg-female/15 text-female border-female/30' : 'bg-ink-950/75 text-fg-muted border-line-strong'">
              {{ t('status.' + a.status) }}
            </span>
          </div>
        </div>
        <div class="px-4 pb-4 -mt-3 relative">
          <div class="flex items-center justify-between gap-2">
            <h3 class="font-display font-semibold text-[17px] text-fg truncate">{{ a.name }}</h3>
            <span :class="sexBadge(a.sex)">{{ sexNotation(a.sex) }}</span>
          </div>
          <p class="text-[12.5px] text-fg-muted italic truncate mt-0.5">{{ a.species }}</p>
          <p class="text-[12.5px] text-moss-400 truncate min-h-[18px]">{{ a.morph }}</p>
          <div class="flex items-center gap-2 mt-3 text-[11.5px] text-fg-faint">
            <span v-if="a.group_name" class="inline-flex items-center gap-1 truncate"><Icon name="group" :size="13" />{{ a.group_name }}</span>
            <span v-else-if="groupList.length" class="inline-flex items-center gap-1"><Icon name="group" :size="13" />{{ t('access.unassigned') }}</span>
            <span v-if="ageText(a)" class="ml-auto num whitespace-nowrap">{{ ageText(a) }}</span>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>
