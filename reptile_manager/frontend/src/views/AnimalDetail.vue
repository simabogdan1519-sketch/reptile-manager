<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '@/i18n'
import { animals as animalsApi, feedings as feedingsApi, sheddings as sheddingsApi, customFields } from '@/api'
import { mediaUrl } from '@/utils/media'
import { fmtDate, fmtDateTime, fmtRelative, ageParts, sexNotation, sexBadge, foodLabel, nowLocalInput, errorMessage } from '@/utils/format'
import Icon from '@/components/Icon.vue'
import EmptyState from '@/components/EmptyState.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const animal = ref(null)
const feedingList = ref([])
const sheddingList = ref([])
const customFieldList = ref([])
const tab = ref('feedings')
const loading = ref(true)
const loadError = ref('')

const emptyFeeding  = () => ({ date: nowLocalInput(), food_type: '', food_size: '', food_count: 1, food_weight_g: '', live: false, accepted: true, notes: '' })
const emptyShedding = () => ({ date: nowLocalInput(), complete: true, in_one_piece: true, pre_shed_days: '', notes: '' })
const feedingForm = ref(emptyFeeding())
const sheddingForm = ref(emptyShedding())
const cfForm = ref({ field_name: '', field_value: '', field_type: 'text' })
const showForm = ref(false)
const saving = ref(false)
const formError = ref('')

onMounted(async () => {
  const id = route.params.id
  try {
    const [aRes, fRes, sRes, cfRes] = await Promise.all([
      animalsApi.get(id), animalsApi.feedings(id), animalsApi.sheddings(id), customFields.list(id),
    ])
    animal.value = aRes.data
    feedingList.value = fRes.data
    sheddingList.value = sRes.data
    customFieldList.value = cfRes.data
  } catch (e) {
    loadError.value = errorMessage(e)
  } finally {
    loading.value = false
  }
})

const age = computed(() => {
  const p = ageParts(animal.value?.date_of_birth)
  return p ? t(`common.age_${p.unit}`, { n: p.value }) : '—'
})
const originLabel = computed(() => {
  const o = animal.value?.origin
  if (!o) return '—'
  const k = 'animal.origin_values.' + o.replace(/ /g, '_')
  const r = t(k)
  return r === k ? o : r
})
const lastFed = computed(() => feedingList.value.find(f => f.accepted))
const reminderText = computed(() => {
  const a = animal.value
  if (!a || a.feeding_reminder_enabled === false) return t('common.off')
  return a.feeding_reminder_days ? t('animal.every_n_days', { n: a.feeding_reminder_days }) : t('animal.reminder_global')
})

const husbandry = computed(() => {
  const a = animal.value
  if (!a) return []
  const out = []
  if (a.temp_day_c != null || a.temp_night_c != null)
    out.push({ num: true, icon: 'thermo', label: t('animal.temperature'), value: [a.temp_day_c != null ? `${a.temp_day_c}°` : null, a.temp_night_c != null ? `${a.temp_night_c}°` : null].filter(Boolean).join(' / '), sub: t('animal.day_night') })
  if (a.humidity_min != null || a.humidity_max != null)
    out.push({ num: true, icon: 'droplet', label: t('animal.humidity'), value: `${a.humidity_min ?? '?'}–${a.humidity_max ?? '?'}%` })
  if (a.lighting_hours != null)
    out.push({ num: true, icon: 'bulb', label: t('animal.photoperiod'), value: `${a.lighting_hours} h` })
  if (a.uv_required != null)
    out.push({ icon: 'sun', label: 'UV', value: a.uv_required ? t('common.required') : t('common.not_required') })
  if (a.terrarium_size)
    out.push({ icon: 'box', label: t('animal.terrarium'), value: a.terrarium_size })
  if (a.substrate)
    out.push({ icon: 'sprout', label: t('animal.substrate'), value: a.substrate })
  return out
})

const tabs = computed(() => [
  { id: 'feedings', label: t('feeding.title'), count: feedingList.value.length, icon: 'feeding' },
  { id: 'sheddings', label: t('shedding.title'), count: sheddingList.value.length, icon: 'shed' },
  { id: 'custom', label: t('animal.custom_fields'), count: customFieldList.value.length, icon: 'tag' },
])

function switchTab(id) { tab.value = id; showForm.value = false; formError.value = '' }

async function submit() {
  saving.value = true
  formError.value = ''
  const id = parseInt(route.params.id)
  try {
    if (tab.value === 'feedings') {
      const p = { ...feedingForm.value, animal_id: id }
      if (!p.food_weight_g) p.food_weight_g = null
      const res = await feedingsApi.create(p)
      feedingList.value.unshift({ ...res.data, animal_name: animal.value.name })
      feedingForm.value = emptyFeeding()
    } else if (tab.value === 'sheddings') {
      const p = { ...sheddingForm.value, animal_id: id }
      if (p.pre_shed_days === '' || p.pre_shed_days == null) p.pre_shed_days = null
      const res = await sheddingsApi.create(p)
      sheddingList.value.unshift({ ...res.data, animal_name: animal.value.name })
      sheddingForm.value = emptyShedding()
    } else {
      const res = await customFields.create(id, cfForm.value)
      customFieldList.value.push(res.data)
      cfForm.value = { field_name: '', field_value: '', field_type: 'text' }
    }
    showForm.value = false
  } catch (e) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function deleteFeeding(id) {
  if (!confirm(t('feeding.confirmDelete'))) return
  await feedingsApi.delete(id)
  feedingList.value = feedingList.value.filter(f => f.id !== id)
}
async function deleteShedding(id) {
  if (!confirm(t('shedding.confirmDelete'))) return
  await sheddingsApi.delete(id)
  sheddingList.value = sheddingList.value.filter(s => s.id !== id)
}
async function deleteCustomField(id) {
  if (!confirm(t('animal.confirm_delete_field'))) return
  await customFields.delete(id)
  customFieldList.value = customFieldList.value.filter(f => f.id !== id)
}
async function deleteAnimal() {
  if (!confirm(`${t('animal.confirmDelete')}\n${animal.value.name}`)) return
  await animalsApi.delete(animal.value.id)
  router.push('/animals')
}

const addLabel = computed(() => tab.value === 'feedings' ? t('feeding.add') : tab.value === 'sheddings' ? t('shedding.add') : t('animal.add_field'))
</script>

<template>
  <div v-if="loading" class="space-y-4">
    <div class="card h-48 animate-pulse" /><div class="card h-24 animate-pulse" />
  </div>

  <div v-else-if="loadError" class="card">
    <EmptyState icon="alert" :title="t('common.not_found')" :text="loadError">
      <button class="btn-secondary" @click="router.push('/animals')"><Icon name="back" :size="16" />{{ t('animal.title') }}</button>
    </EmptyState>
  </div>

  <div v-else-if="animal" class="animate-rise">
    <!-- Hero -->
    <section class="card p-0 overflow-hidden mb-4">
      <div class="grid md:grid-cols-[260px_1fr]">
        <div class="relative aspect-[4/3] md:aspect-auto md:min-h-[240px] bg-ink-850 border-b md:border-b-0 md:border-r border-line">
          <img v-if="animal.photo_url" :src="mediaUrl(animal.photo_url)" :alt="animal.name" class="absolute inset-0 w-full h-full object-cover" />
          <div v-else class="absolute inset-0 grid place-items-center"><Icon name="reptile" :size="64" :stroke="1.1" class="text-line-strong" /></div>
          <button class="absolute top-3 left-3 btn-secondary btn-sm btn-icon !bg-ink-950/70 backdrop-blur" @click="router.push('/animals')" :title="t('common.back')">
            <Icon name="back" :size="16" />
          </button>
        </div>

        <div class="p-5 md:p-7 flex flex-col">
          <div class="flex flex-wrap items-center gap-2 mb-2">
            <span v-if="animal.tracking_id" class="eyebrow num !text-moss-400">#{{ animal.tracking_id }}</span>
            <span :class="sexBadge(animal.sex)">{{ sexNotation(animal.sex) }}</span>
            <span v-if="animal.status !== 'active'" :class="animal.status === 'sold' ? 'badge-blue' : 'badge-gray'">{{ t('status.' + animal.status) }}</span>
            <span v-if="animal.group_name" class="badge-gray"><Icon name="group" :size="12" />{{ animal.group_name }}</span>
          </div>
          <h1 class="font-display text-[34px] md:text-[42px] leading-[1.02] font-semibold text-fg">{{ animal.name }}</h1>
          <p class="text-fg-muted mt-1.5"><span class="italic">{{ animal.species }}</span><span v-if="animal.common_name"> · {{ animal.common_name }}</span></p>
          <p v-if="animal.morph" class="text-moss-400 font-medium mt-0.5">{{ animal.morph }}</p>

          <div class="flex flex-wrap gap-2 mt-5 md:mt-auto pt-2">
            <button class="btn-primary btn-sm" @click="router.push(`/animals/${animal.id}/edit`)"><Icon name="edit" :size="15" />{{ t('common.edit') }}</button>
            <button class="btn-secondary btn-sm" @click="router.push(`/animals/${animal.id}/tree`)"><Icon name="tree" :size="15" />{{ t('animal.tree') }}</button>
            <button class="btn-secondary btn-sm" @click="router.push(`/animals/${animal.id}/label`)"><Icon name="tag" :size="15" />{{ t('animal.label') }}</button>
            <button class="btn-secondary btn-sm" @click="router.push(`/export?ids=${animal.id}`)"><Icon name="certificate" :size="15" />{{ t('animal.certificate') }}</button>
            <button class="btn-danger btn-sm btn-icon ml-auto" :title="t('common.delete')" @click="deleteAnimal"><Icon name="trash" :size="15" /></button>
          </div>
        </div>
      </div>

      <!-- Vitals strip -->
      <div class="grid grid-cols-2 sm:grid-cols-5 border-t border-line divide-x divide-y sm:divide-y-0 divide-line">
        <div class="vital"><span class="eyebrow">{{ t('animal.weight_short') }}</span><span class="vital-v">{{ animal.weight_g ? animal.weight_g : '—' }}<small v-if="animal.weight_g">g</small></span></div>
        <div class="vital"><span class="eyebrow">{{ t('animal.length_short') }}</span><span class="vital-v">{{ animal.length_cm ? animal.length_cm : '—' }}<small v-if="animal.length_cm">cm</small></span></div>
        <div class="vital"><span class="eyebrow">{{ t('animal.age') }}</span><span class="vital-v">{{ age }}</span></div>
        <div class="vital"><span class="eyebrow">{{ t('animal.last_fed') }}</span><span class="vital-v">{{ lastFed ? fmtRelative(lastFed.date) : '—' }}</span></div>
        <div class="vital col-span-2 sm:col-span-1"><span class="eyebrow">{{ t('animal.feeding_reminder') }}</span><span class="vital-v">{{ reminderText }}</span></div>
      </div>
    </section>

    <!-- Info grid -->
    <div v-if="husbandry.length || animal.mother || animal.father || animal.notes || animal.date_of_birth || animal.origin"
         class="grid lg:grid-cols-[1.4fr_1fr] gap-4 mb-6">
      <section v-if="husbandry.length" class="card">
        <h2 class="section-title mb-4">{{ t('animal.husbandry') }}</h2>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          <div v-for="h in husbandry" :key="h.label" class="tile">
            <div class="flex items-center gap-1.5 text-fg-faint mb-1.5"><Icon :name="h.icon" :size="14" /><span class="text-[11.5px] font-medium">{{ h.label }}</span></div>
            <div class="text-fg font-semibold text-[14.5px] truncate" :class="{ num: h.num }">{{ h.value }}</div>
            <div v-if="h.sub" class="text-[10.5px] text-fg-faint">{{ h.sub }}</div>
          </div>
        </div>
      </section>

      <section class="card space-y-4" :class="!husbandry.length ? 'lg:col-span-2' : ''">
        <h2 class="section-title">{{ t('animal.details') }}</h2>
        <dl class="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
          <div><dt class="text-fg-faint text-xs mb-0.5">{{ t('animal.dob') }}</dt><dd class="text-fg">{{ fmtDate(animal.date_of_birth) }}</dd></div>
          <div><dt class="text-fg-faint text-xs mb-0.5">{{ t('animal.acquired') }}</dt><dd class="text-fg">{{ fmtDate(animal.date_acquired) }}</dd></div>
          <div class="col-span-2"><dt class="text-fg-faint text-xs mb-0.5">{{ t('animal.origin') }}</dt><dd class="text-fg">{{ originLabel }}</dd></div>
        </dl>
        <div v-if="animal.mother || animal.father">
          <p class="text-fg-faint text-xs mb-2">{{ t('animal.parents') }}</p>
          <div class="grid grid-cols-2 gap-2">
            <button v-for="p in [animal.mother && { ...animal.mother, sx: 'female' }, animal.father && { ...animal.father, sx: 'male' }].filter(Boolean)" :key="p.id"
                    class="tile text-left hover:border-line-strong transition-colors" @click="router.push(`/animals/${p.id}`)">
              <span :class="sexBadge(p.sx)">{{ sexNotation(p.sx) }}</span>
              <div class="font-semibold text-fg mt-1.5 truncate">{{ p.name }}</div>
              <div class="text-[11.5px] text-fg-faint truncate">{{ p.morph || p.species }}</div>
            </button>
          </div>
        </div>
        <div v-if="animal.notes">
          <p class="text-fg-faint text-xs mb-1">{{ t('animal.notes') }}</p>
          <p class="text-sm text-fg-muted whitespace-pre-line leading-relaxed">{{ animal.notes }}</p>
        </div>
      </section>
    </div>

    <!-- Records -->
    <section class="panel">
      <div class="flex items-center justify-between gap-3 pr-3 border-b border-line">
        <div class="tabs !border-b-0 px-2 scrollbar-none">
          <button v-for="tb in tabs" :key="tb.id" class="tab" :class="{ on: tab === tb.id }" @click="switchTab(tb.id)">
            {{ tb.label }}<span class="count">{{ tb.count }}</span>
          </button>
        </div>
        <button class="btn-primary btn-sm flex-shrink-0" @click="showForm = !showForm">
          <Icon :name="showForm ? 'x' : 'plus'" :size="15" /><span class="hidden sm:inline">{{ showForm ? t('common.cancel') : addLabel }}</span>
        </button>
      </div>

      <!-- Inline form -->
      <form v-if="showForm" class="p-5 border-b border-line bg-ink-950/40 animate-rise" @submit.prevent="submit">
        <div v-if="formError" class="alert-error mb-4"><Icon name="alert" :size="16" />{{ formError }}</div>

        <div v-if="tab === 'feedings'" class="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div><label>{{ t('feeding.date') }}</label><input type="datetime-local" v-model="feedingForm.date" required /></div>
          <div><label>{{ t('feeding.food_type') }} *</label><input v-model="feedingForm.food_type" :placeholder="t('feeding.food_type_ph')" required /></div>
          <div><label>{{ t('feeding.food_size') }}</label><input v-model="feedingForm.food_size" :placeholder="t('feeding.food_size_ph')" /></div>
          <div class="grid grid-cols-2 gap-3">
            <div><label>{{ t('feeding.count') }}</label><input type="number" v-model="feedingForm.food_count" min="1" /></div>
            <div><label>{{ t('feeding.weight') }}</label><input type="number" v-model="feedingForm.food_weight_g" step="0.1" min="0" /></div>
          </div>
          <div class="sm:col-span-2 lg:col-span-4 flex flex-wrap gap-2">
            <label class="option" :class="{ on: feedingForm.accepted }"><input type="checkbox" v-model="feedingForm.accepted" /><span class="option-title">{{ t('feeding.accepted') }}</span></label>
            <label class="option" :class="{ on: feedingForm.live }"><input type="checkbox" v-model="feedingForm.live" /><span class="option-title">{{ t('feeding.live') }}</span></label>
          </div>
          <div class="sm:col-span-2 lg:col-span-4"><label>{{ t('feeding.notes') }}</label><textarea v-model="feedingForm.notes" rows="2" /></div>
        </div>

        <div v-else-if="tab === 'sheddings'" class="grid sm:grid-cols-2 gap-3">
          <div><label>{{ t('shedding.date') }}</label><input type="datetime-local" v-model="sheddingForm.date" required /></div>
          <div><label>{{ t('shedding.pre_shed_days') }}</label><input type="number" v-model="sheddingForm.pre_shed_days" min="0" placeholder="7" /></div>
          <div class="sm:col-span-2 flex flex-wrap gap-2">
            <label class="option" :class="{ on: sheddingForm.complete }"><input type="checkbox" v-model="sheddingForm.complete" /><span class="option-title">{{ t('shedding.complete') }}</span></label>
            <label class="option" :class="{ on: sheddingForm.in_one_piece }"><input type="checkbox" v-model="sheddingForm.in_one_piece" /><span class="option-title">{{ t('shedding.in_one_piece') }}</span></label>
          </div>
          <div class="sm:col-span-2"><label>{{ t('shedding.notes') }}</label><textarea v-model="sheddingForm.notes" rows="2" /></div>
        </div>

        <div v-else class="grid sm:grid-cols-3 gap-3">
          <div><label>{{ t('animal.field_name') }} *</label><input v-model="cfForm.field_name" required :placeholder="t('animal.field_name_ph')" /></div>
          <div><label>{{ t('common.value') }}</label><input v-model="cfForm.field_value" /></div>
          <div>
            <label>{{ t('animal.field_type') }}</label>
            <select v-model="cfForm.field_type">
              <option value="text">{{ t('animal.field_types.text') }}</option>
              <option value="number">{{ t('animal.field_types.number') }}</option>
              <option value="date">{{ t('animal.field_types.date') }}</option>
              <option value="boolean">{{ t('animal.field_types.boolean') }}</option>
            </select>
          </div>
        </div>

        <div class="flex gap-2 mt-4">
          <button type="submit" class="btn-primary btn-sm" :disabled="saving">{{ saving ? t('common.saving') : t('common.save') }}</button>
          <button type="button" class="btn-ghost btn-sm" @click="showForm = false">{{ t('common.cancel') }}</button>
        </div>
      </form>

      <!-- Feedings -->
      <template v-if="tab === 'feedings'">
        <EmptyState v-if="!feedingList.length" icon="feeding" :title="t('feeding.noEntries')" />
        <div v-else class="overflow-x-auto">
          <table class="data-table">
            <thead><tr><th>{{ t('feeding.date') }}</th><th>{{ t('feeding.food_type') }}</th><th>{{ t('common.status') }}</th><th class="hidden md:table-cell">{{ t('feeding.notes') }}</th><th class="w-10"></th></tr></thead>
            <tbody>
              <tr v-for="f in feedingList" :key="f.id">
                <td class="whitespace-nowrap text-fg-muted num text-[12.5px]">{{ fmtDateTime(f.date) }}</td>
                <td class="text-fg">
                  {{ foodLabel(f) }}
                  <span v-if="f.food_weight_g" class="text-fg-faint num"> · {{ f.food_weight_g }} g</span>
                  <span v-if="f.live" class="badge-blue ml-1.5">{{ t('feeding.live') }}</span>
                </td>
                <td><span :class="f.accepted ? 'badge-green' : 'badge-red'"><span class="dot" />{{ f.accepted ? t('feeding.accepted_label') : t('feeding.rejected_label') }}</span></td>
                <td class="hidden md:table-cell text-fg-faint max-w-[240px] truncate">{{ f.notes }}</td>
                <td><button class="icon-btn danger" @click="deleteFeeding(f.id)"><Icon name="trash" :size="15" /></button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- Sheddings -->
      <template v-if="tab === 'sheddings'">
        <EmptyState v-if="!sheddingList.length" icon="shed" :title="t('shedding.noEntries')" />
        <div v-else class="overflow-x-auto">
          <table class="data-table">
            <thead><tr><th>{{ t('shedding.date') }}</th><th>{{ t('shedding.blue_phase') }}</th><th>{{ t('common.status') }}</th><th class="hidden md:table-cell">{{ t('shedding.notes') }}</th><th class="w-10"></th></tr></thead>
            <tbody>
              <tr v-for="s in sheddingList" :key="s.id">
                <td class="whitespace-nowrap text-fg-muted num text-[12.5px]">{{ fmtDateTime(s.date) }}</td>
                <td class="text-fg-muted num">{{ s.pre_shed_days != null ? t('common.n_days', { n: s.pre_shed_days }) : '—' }}</td>
                <td class="space-x-1">
                  <span :class="s.complete ? 'badge-green' : 'badge-yellow'"><span class="dot" />{{ s.complete ? t('shedding.complete_label') : t('shedding.incomplete_label') }}</span>
                  <span v-if="!s.in_one_piece" class="badge-red">{{ t('shedding.torn') }}</span>
                </td>
                <td class="hidden md:table-cell text-fg-faint max-w-[240px] truncate">{{ s.notes }}</td>
                <td><button class="icon-btn danger" @click="deleteShedding(s.id)"><Icon name="trash" :size="15" /></button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- Custom fields -->
      <template v-if="tab === 'custom'">
        <EmptyState v-if="!customFieldList.length" icon="tag" :title="t('animal.no_fields')" :text="t('animal.no_fields_text')" />
        <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-2.5 p-4">
          <div v-for="cf in customFieldList" :key="cf.id" class="tile flex items-start justify-between gap-2">
            <div class="min-w-0">
              <div class="eyebrow mb-1 truncate">{{ cf.field_name }}</div>
              <div class="text-fg font-medium truncate">{{ cf.field_value ?? '—' }}</div>
            </div>
            <button class="icon-btn danger -mr-1 -mt-1" @click="deleteCustomField(cf.id)"><Icon name="trash" :size="14" /></button>
          </div>
        </div>
      </template>
    </section>
  </div>
</template>

<style scoped>
.vital { @apply flex flex-col gap-1.5 px-5 py-4; }
.vital-v { @apply font-display text-[19px] font-semibold text-fg truncate; }
.vital-v small { @apply text-[12px] text-fg-faint font-sans font-medium ml-0.5; }
</style>
