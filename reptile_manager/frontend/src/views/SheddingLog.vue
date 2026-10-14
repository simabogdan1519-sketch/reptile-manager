<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/i18n'
import { sheddings as sheddingsApi, animals as animalsApi } from '@/api'
import { fmtDateTime, nowLocalInput, errorMessage } from '@/utils/format'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import EmptyState from '@/components/EmptyState.vue'
import AnimalAvatar from '@/components/AnimalAvatar.vue'

const { t } = useI18n()
const router = useRouter()

const list = ref([])
const allAnimals = ref([])
const filterAnimal = ref('')
const loading = ref(true)
const showForm = ref(false)
const saving = ref(false)
const formError = ref('')
const empty = () => ({ animal_id: '', date: nowLocalInput(), complete: true, in_one_piece: true, pre_shed_days: '', notes: '' })
const form = ref(empty())

const animalById = computed(() => Object.fromEntries(allAnimals.value.map(a => [a.id, a])))
const completeRate = computed(() => list.value.length ? Math.round(list.value.filter(s => s.complete).length / list.value.length * 100) : null)

onMounted(async () => {
  const [sRes, aRes] = await Promise.all([
    sheddingsApi.list({ limit: 200 }),
    animalsApi.list({ active_only: false, limit: 500 }),
  ])
  list.value = sRes.data
  allAnimals.value = aRes.data
  loading.value = false
})

watch(filterAnimal, async () => {
  loading.value = true
  const params = filterAnimal.value ? { animal_id: filterAnimal.value, limit: 200 } : { limit: 200 }
  list.value = (await sheddingsApi.list(params)).data
  loading.value = false
})

async function addShedding() {
  saving.value = true
  formError.value = ''
  try {
    const payload = { ...form.value, animal_id: parseInt(form.value.animal_id) }
    if (payload.pre_shed_days === '' || payload.pre_shed_days == null) payload.pre_shed_days = null
    const res = await sheddingsApi.create(payload)
    list.value.unshift({ ...res.data, animal_name: animalById.value[res.data.animal_id]?.name })
    showForm.value = false
    form.value = empty()
  } catch (e) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function deleteShedding(id) {
  if (!confirm(t('shedding.confirmDelete'))) return
  await sheddingsApi.delete(id)
  list.value = list.value.filter(s => s.id !== id)
}
</script>

<template>
  <div>
    <PageHeader :eyebrow="t('shedding.eyebrow')" :title="t('shedding.title')">
      <template #subtitle>
        <span class="num">{{ t('common.n_entries', { n: list.length }) }}</span>
        <template v-if="completeRate !== null"> · <span class="num">{{ t('shedding.complete_rate', { n: completeRate }) }}</span></template>
      </template>
      <template #actions>
        <select v-model="filterAnimal" class="w-48 h-9">
          <option value="">{{ t('common.all_animals') }}</option>
          <option v-for="a in allAnimals" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>
        <button class="btn-primary" @click="showForm = !showForm">
          <Icon :name="showForm ? 'x' : 'plus'" :size="16" />{{ showForm ? t('common.cancel') : t('shedding.add') }}
        </button>
      </template>
    </PageHeader>

    <form v-if="showForm" class="card mb-5 animate-rise" @submit.prevent="addShedding">
      <h2 class="section-title mb-4">{{ t('shedding.add') }}</h2>
      <div v-if="formError" class="alert-error mb-4"><Icon name="alert" :size="16" />{{ formError }}</div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <div>
          <label>{{ t('feeding.animal') }} *</label>
          <select v-model="form.animal_id" required>
            <option value="" disabled>{{ t('common.choose') }}</option>
            <option v-for="a in allAnimals.filter(a => a.is_active)" :key="a.id" :value="a.id">{{ a.name }} · {{ a.species }}</option>
          </select>
        </div>
        <div><label>{{ t('shedding.date') }}</label><input type="datetime-local" v-model="form.date" required /></div>
        <div><label>{{ t('shedding.pre_shed_days') }}</label><input type="number" v-model="form.pre_shed_days" min="0" placeholder="7" class="num" /></div>
        <div class="sm:col-span-2 lg:col-span-3 flex flex-wrap gap-2">
          <label class="option" :class="{ on: form.complete }"><input type="checkbox" v-model="form.complete" /><span class="option-title">{{ t('shedding.complete') }}</span></label>
          <label class="option" :class="{ on: form.in_one_piece }"><input type="checkbox" v-model="form.in_one_piece" /><span class="option-title">{{ t('shedding.in_one_piece') }}</span></label>
        </div>
        <div class="sm:col-span-2 lg:col-span-3"><label>{{ t('shedding.notes') }}</label><textarea v-model="form.notes" rows="2" /></div>
      </div>
      <div class="flex gap-2 mt-4">
        <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? t('common.saving') : t('common.save') }}</button>
        <button type="button" class="btn-ghost" @click="showForm = false">{{ t('common.cancel') }}</button>
      </div>
    </form>

    <section class="panel">
      <div v-if="loading" class="p-10 text-center text-fg-faint">{{ t('common.loading') }}</div>
      <EmptyState v-else-if="!list.length" icon="shed" :title="t('shedding.noEntries')" :text="t('shedding.empty_text')" />
      <div v-else class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('feeding.animal') }}</th>
              <th>{{ t('shedding.date') }}</th>
              <th class="hidden sm:table-cell">{{ t('shedding.blue_phase') }}</th>
              <th>{{ t('common.status') }}</th>
              <th class="hidden lg:table-cell">{{ t('shedding.notes') }}</th>
              <th class="w-10"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in list" :key="s.id">
              <td>
                <button class="flex items-center gap-2.5 text-left group" @click="router.push(`/animals/${s.animal_id}`)">
                  <AnimalAvatar :animal="animalById[s.animal_id] || { name: s.animal_name }" size="w-8 h-8" rounded="rounded-lg" />
                  <span class="font-semibold text-fg group-hover:text-moss-400 transition-colors whitespace-nowrap">{{ s.animal_name }}</span>
                </button>
              </td>
              <td class="whitespace-nowrap text-fg-muted num text-[12.5px]">{{ fmtDateTime(s.date) }}</td>
              <td class="hidden sm:table-cell text-fg-muted num">{{ s.pre_shed_days != null ? t('common.n_days', { n: s.pre_shed_days }) : '—' }}</td>
              <td class="whitespace-nowrap space-x-1">
                <span :class="s.complete ? 'badge-green' : 'badge-yellow'"><span class="dot" />{{ s.complete ? t('shedding.complete_label') : t('shedding.incomplete_label') }}</span>
                <span v-if="!s.in_one_piece" class="badge-red">{{ t('shedding.torn') }}</span>
              </td>
              <td class="hidden lg:table-cell text-fg-faint max-w-[220px] truncate">{{ s.notes }}</td>
              <td><button class="icon-btn danger" @click="deleteShedding(s.id)"><Icon name="trash" :size="15" /></button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
