<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '@/i18n'
import { feedings as feedingsApi, animals as animalsApi } from '@/api'
import { fmtDateTime, foodLabel, nowLocalInput, errorMessage } from '@/utils/format'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import EmptyState from '@/components/EmptyState.vue'
import AnimalAvatar from '@/components/AnimalAvatar.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const list = ref([])
const allAnimals = ref([])
const filterAnimal = ref('')
const loading = ref(true)

const empty = () => ({ animal_id: '', date: nowLocalInput(), food_type: '', food_size: '', food_count: 1, food_weight_g: '', live: false, accepted: true, notes: '' })
const showForm = ref(route.query.new === '1')
const saving = ref(false)
const formError = ref('')
const form = ref(empty())

const animalById = computed(() => Object.fromEntries(allAnimals.value.map(a => [a.id, a])))
const acceptance = computed(() => list.value.length ? Math.round(list.value.filter(f => f.accepted).length / list.value.length * 100) : null)

onMounted(async () => {
  const [fRes, aRes] = await Promise.all([
    feedingsApi.list({ limit: 200 }),
    animalsApi.list({ active_only: false, limit: 500 }),
  ])
  list.value = fRes.data
  allAnimals.value = aRes.data
  loading.value = false
})

watch(filterAnimal, async () => {
  loading.value = true
  const params = filterAnimal.value ? { animal_id: filterAnimal.value, limit: 200 } : { limit: 200 }
  list.value = (await feedingsApi.list(params)).data
  loading.value = false
})

async function addFeeding() {
  saving.value = true
  formError.value = ''
  try {
    const payload = { ...form.value, animal_id: parseInt(form.value.animal_id) }
    if (!payload.food_weight_g) payload.food_weight_g = null
    const res = await feedingsApi.create(payload)
    list.value.unshift({ ...res.data, animal_name: animalById.value[res.data.animal_id]?.name })
    const keep = { food_type: form.value.food_type, food_size: form.value.food_size }
    form.value = { ...empty(), ...keep }
    showForm.value = false
    if (route.query.new) router.replace({ query: {} })
  } catch (e) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function deleteFeeding(id) {
  if (!confirm(t('feeding.confirmDelete'))) return
  await feedingsApi.delete(id)
  list.value = list.value.filter(f => f.id !== id)
}
</script>

<template>
  <div>
    <PageHeader :eyebrow="t('feeding.eyebrow')" :title="t('feeding.title')">
      <template #subtitle>
        <span class="num">{{ t('common.n_entries', { n: list.length }) }}</span>
        <template v-if="acceptance !== null"> · <span class="num">{{ t('feeding.acceptance', { n: acceptance }) }}</span></template>
      </template>
      <template #actions>
        <select v-model="filterAnimal" class="w-48 h-9">
          <option value="">{{ t('common.all_animals') }}</option>
          <option v-for="a in allAnimals" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>
        <button class="btn-primary" @click="showForm = !showForm">
          <Icon :name="showForm ? 'x' : 'plus'" :size="16" />{{ showForm ? t('common.cancel') : t('feeding.add') }}
        </button>
      </template>
    </PageHeader>

    <form v-if="showForm" class="card mb-5 animate-rise" @submit.prevent="addFeeding">
      <h2 class="section-title mb-4">{{ t('feeding.add') }}</h2>
      <div v-if="formError" class="alert-error mb-4"><Icon name="alert" :size="16" />{{ formError }}</div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="lg:col-span-2">
          <label>{{ t('feeding.animal') }} *</label>
          <select v-model="form.animal_id" required>
            <option value="" disabled>{{ t('common.choose') }}</option>
            <option v-for="a in allAnimals.filter(a => a.is_active)" :key="a.id" :value="a.id">{{ a.name }} · {{ a.species }}</option>
          </select>
        </div>
        <div class="lg:col-span-2"><label>{{ t('feeding.date') }}</label><input type="datetime-local" v-model="form.date" required /></div>
        <div><label>{{ t('feeding.food_type') }} *</label><input v-model="form.food_type" :placeholder="t('feeding.food_type_ph')" required /></div>
        <div><label>{{ t('feeding.food_size') }}</label><input v-model="form.food_size" :placeholder="t('feeding.food_size_ph')" /></div>
        <div><label>{{ t('feeding.count') }}</label><input type="number" v-model="form.food_count" min="1" class="num" /></div>
        <div><label>{{ t('feeding.weight') }}</label><input type="number" v-model="form.food_weight_g" step="0.1" class="num" /></div>
        <div class="sm:col-span-2 lg:col-span-4 flex flex-wrap gap-2">
          <label class="option" :class="{ on: form.accepted }"><input type="checkbox" v-model="form.accepted" /><span class="option-title">{{ t('feeding.accepted') }}</span></label>
          <label class="option" :class="{ on: form.live }"><input type="checkbox" v-model="form.live" /><span class="option-title">{{ t('feeding.live') }}</span></label>
        </div>
        <div class="sm:col-span-2 lg:col-span-4"><label>{{ t('feeding.notes') }}</label><textarea v-model="form.notes" rows="2" /></div>
      </div>
      <div class="flex gap-2 mt-4">
        <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? t('common.saving') : t('common.save') }}</button>
        <button type="button" class="btn-ghost" @click="showForm = false">{{ t('common.cancel') }}</button>
      </div>
    </form>

    <section class="panel">
      <div v-if="loading" class="p-10 text-center text-fg-faint">{{ t('common.loading') }}</div>
      <EmptyState v-else-if="!list.length" icon="feeding" :title="t('feeding.noEntries')" :text="t('feeding.empty_text')" />
      <div v-else class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('feeding.animal') }}</th>
              <th>{{ t('feeding.date') }}</th>
              <th>{{ t('feeding.food_type') }}</th>
              <th class="hidden sm:table-cell">{{ t('feeding.weight') }}</th>
              <th>{{ t('common.status') }}</th>
              <th class="hidden lg:table-cell">{{ t('feeding.notes') }}</th>
              <th class="w-10"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in list" :key="f.id">
              <td>
                <button class="flex items-center gap-2.5 text-left group" @click="router.push(`/animals/${f.animal_id}`)">
                  <AnimalAvatar :animal="animalById[f.animal_id] || { name: f.animal_name }" size="w-8 h-8" rounded="rounded-lg" />
                  <span class="font-semibold text-fg group-hover:text-moss-400 transition-colors whitespace-nowrap">{{ f.animal_name }}</span>
                </button>
              </td>
              <td class="whitespace-nowrap text-fg-muted num text-[12.5px]">{{ fmtDateTime(f.date) }}</td>
              <td class="text-fg whitespace-nowrap">
                {{ foodLabel(f) }}
                <span v-if="f.live" class="badge-blue ml-1.5">{{ t('feeding.live') }}</span>
              </td>
              <td class="hidden sm:table-cell text-fg-muted num">{{ f.food_weight_g ? `${f.food_weight_g} g` : '—' }}</td>
              <td><span :class="f.accepted ? 'badge-green' : 'badge-red'"><span class="dot" />{{ f.accepted ? t('feeding.accepted_label') : t('feeding.rejected_label') }}</span></td>
              <td class="hidden lg:table-cell text-fg-faint max-w-[220px] truncate">{{ f.notes }}</td>
              <td><button class="icon-btn danger" @click="deleteFeeding(f.id)"><Icon name="trash" :size="15" /></button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
