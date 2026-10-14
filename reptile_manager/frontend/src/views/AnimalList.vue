<script setup>
import { useI18n } from '@/i18n'
import { ref, computed, watch, onMounted } from 'vue'
import { mediaUrl } from '@/utils/media'
import { useRouter } from 'vue-router'
import { animals as animalsApi, groups as groupsApi } from '@/api'

const { t } = useI18n()

const router = useRouter()
const list = ref([])
const search = ref('')
const showInactive = ref(false)
const loading = ref(true)
const groupList = ref([])
const groupFilter = ref('all')   // 'all' | 'none' | <id>
const filtered = computed(() => {
  if (groupFilter.value === 'all')  return list.value
  if (groupFilter.value === 'none') return list.value.filter(a => !a.group_id)
  return list.value.filter(a => a.group_id === groupFilter.value)
})

async function load() {
  loading.value = true
  try {
    const res = await animalsApi.list({ search: search.value || undefined, active_only: !showInactive.value })
    list.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  load()
  try { groupList.value = (await groupsApi.list()).data } catch { /* non-critical */ }
})
watch([search, showInactive], load)


function sexNotation(sex) {
  if (sex === 'male')   return '1.0.0'
  if (sex === 'female') return '0.1.0'
  return '0.0.1'
}

function sexIcon(sex) {
  return sex === 'male' ? '♂' : sex === 'female' ? '♀' : '?'
}
function sexClass(sex) {
  return sex === 'male' ? 'text-blue-400' : sex === 'female' ? 'text-pink-400' : 'text-slate-500'
}

async function deleteAnimal(id) {
  if (!confirm(t('animal.confirmDelete'))) return
  await animalsApi.delete(id)
  load()
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
      <h1 class="text-2xl font-bold text-slate-200">Tiere</h1>
      <div class="flex gap-3">
        <label class="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
          <input type="checkbox" v-model="showInactive" class="w-4 h-4" />
          {{ t('animal.showInactive') }}
        </label>
        <button class="btn-primary btn-sm" @click="router.push('/animals/new')">
          + {{ t('animal.add') }}
        </button>
      </div>
    </div>

    <!-- Search -->
    <div class="mb-6 flex flex-col sm:flex-row gap-3">
      <input v-model="search" type="search" placeholder="Suche nach Name, Art, Morph…" class="flex-1" />
      <select v-if="groupList.length > 1 || (groupList.length && list.some(a => !a.group_id))"
              v-model="groupFilter" class="sm:w-56">
        <option value="all">👥 {{ t('access.all_groups') }}</option>
        <option v-for="g in groupList" :key="g.id" :value="g.id">{{ g.name }}</option>
        <option v-if="list.some(a => !a.group_id)" value="none">{{ t('access.unassigned') }}</option>
      </select>
    </div>

    <div v-if="loading" class="text-slate-500 text-center py-16">Lade…</div>

    <div v-else-if="!filtered.length" class="text-center py-16 text-slate-500">
      <div class="text-4xl mb-3">🦎</div>
      <p>{{ t('animal.noAnimals') }}</p>
      <button class="btn-primary mt-4" @click="router.push('/animals/new')">{{ t('animal.add') }}</button>
    </div>

    <!-- Grid -->
    <div v-else class="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
      <div
        v-for="a in filtered"
        :key="a.id"
        class="card hover:border-brand-500 border border-surface-600 transition-all cursor-pointer group"
        @click="router.push(`/animals/${a.id}`)"
      >
        <!-- Photo / placeholder -->
        <div class="aspect-square rounded-lg mb-3 overflow-hidden bg-surface-600 flex items-center justify-center">
          <img v-if="a.photo_url" :src="mediaUrl(a.photo_url)" :alt="a.name" class="w-full h-full object-cover" />
          <span v-else class="text-5xl opacity-30">🦎</span>
        </div>

        <!-- Info -->
        <div class="flex items-start justify-between">
          <div class="min-w-0">
            <div class="flex items-center gap-1.5">
              <span class="font-semibold text-slate-200 truncate">{{ a.name }}</span>
              <span :class="sexClass(a.sex)" class="text-sm font-bold">{{ sexNotation(a.sex) }}</span>
            </div>
            <p class="text-xs text-slate-500 italic truncate">{{ a.species }}</p>
            <p v-if="a.morph" class="text-xs text-brand-400 truncate">{{ a.morph }}</p>
            <span v-if="a.group_name" class="badge-blue mt-1 max-w-full truncate">👥 {{ a.group_name }}</span>
            <span v-else-if="groupList.length" class="badge-gray mt-1">{{ t('access.unassigned') }}</span>
          </div>
          <span v-if="!a.is_active" class="badge-gray ml-2 flex-shrink-0">Inaktiv</span>
        </div>

        <!-- Quick actions (on hover) -->
        <div class="flex gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity" @click.stop>
          <button class="btn-secondary btn-sm flex-1 text-xs" @click="router.push(`/animals/${a.id}/edit`)">
            Bearbeiten
          </button>
          <button class="btn-secondary btn-sm text-xs" @click="router.push(`/animals/${a.id}/tree`)"
                  title="Stammbaum">🌳</button>
          <button class="btn-secondary btn-sm text-xs" @click="router.push(`/export?ids=${a.id}`)"
                  title="Herkunftsnachweis">📜</button>
          <button class="btn-danger btn-sm text-xs" @click="deleteAnimal(a.id)">
            🗑
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
