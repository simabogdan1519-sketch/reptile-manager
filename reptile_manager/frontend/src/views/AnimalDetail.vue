<script setup>
import { useI18n } from '@/i18n'
import { ref, onMounted } from 'vue'
import { mediaUrl } from '@/utils/media'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n()
import { animals as animalsApi, feedings as feedingsApi, sheddings as sheddingsApi, customFields } from '@/api'

const route = useRoute()
const router = useRouter()
const animal = ref(null)
const feedingList = ref([])
const sheddingList = ref([])
const customFieldList = ref([])
const tab = ref('feedings')
const loading = ref(true)

// New feeding form
const feedingForm = ref({ date: new Date().toISOString().slice(0,16), food_type: '', food_size: '', food_count: 1, food_weight_g: '', live: false, accepted: true, notes: '' })
const showFeedingForm = ref(false)
const savingFeeding = ref(false)

// New shedding form
const sheddingForm = ref({ date: new Date().toISOString().slice(0,16), complete: true, in_one_piece: true, pre_shed_days: '', notes: '' })
const showSheddingForm = ref(false)
const savingShedding = ref(false)

// Custom field form
const cfForm = ref({ field_name: '', field_value: '', field_type: 'text' })
const showCfForm = ref(false)
const savingCf = ref(false)

onMounted(async () => {
  const id = route.params.id
  const [aRes, fRes, sRes, cfRes] = await Promise.all([
    animalsApi.get(id),
    animalsApi.feedings(id),
    animalsApi.sheddings(id),
    customFields.list(id),
  ])
  animal.value = aRes.data
  feedingList.value = fRes.data
  sheddingList.value = sRes.data
  customFieldList.value = cfRes.data
  loading.value = false
})

function fmtDate(d) { return d ? new Date(d).toLocaleDateString('de-DE') : '—' }
function fmtDateTime(d) { return d ? new Date(d).toLocaleString('de-DE', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' }) : '—' }
function age(dob) {
  if (!dob) return null
  const d = new Date(dob), now = new Date()
  const months = (now.getFullYear() - d.getFullYear()) * 12 + now.getMonth() - d.getMonth()
  return months < 24 ? `${months} Monate` : `${(months/12).toFixed(1)} Jahre`
}

async function addFeeding() {
  savingFeeding.value = true
  try {
    const payload = { ...feedingForm.value, animal_id: parseInt(route.params.id) }
    if (!payload.food_weight_g) payload.food_weight_g = null
    const res = await feedingsApi.create(payload)
    feedingList.value.unshift({ ...res.data, animal_name: animal.value.name })
    showFeedingForm.value = false
    feedingForm.value = { date: new Date().toISOString().slice(0,16), food_type: '', food_size: '', food_count: 1, food_weight_g: '', live: false, accepted: true, notes: '' }
  } finally {
    savingFeeding.value = false
  }
}

async function addShedding() {
  savingShedding.value = true
  try {
    const payload = { ...sheddingForm.value, animal_id: parseInt(route.params.id) }
    if (!payload.pre_shed_days) payload.pre_shed_days = null
    const res = await sheddingsApi.create(payload)
    sheddingList.value.unshift({ ...res.data, animal_name: animal.value.name })
    showSheddingForm.value = false
    sheddingForm.value = { date: new Date().toISOString().slice(0,16), complete: true, in_one_piece: true, pre_shed_days: '', notes: '' }
  } finally {
    savingShedding.value = false
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

async function addCustomField() {
  savingCf.value = true
  try {
    const res = await customFields.create(route.params.id, cfForm.value)
    customFieldList.value.push(res.data)
    showCfForm.value = false
    cfForm.value = { field_name: '', field_value: '', field_type: 'text' }
  } finally {
    savingCf.value = false
  }
}

async function deleteCustomField(id) {
  await customFields.delete(id)
  customFieldList.value = customFieldList.value.filter(f => f.id !== id)
}

function sexNotation(sex) {
  if (sex === 'male')   return '1.0.0'
  if (sex === 'female') return '0.1.0'
  return '0.0.1'
}

</script>

<template>
  <div v-if="loading" class="text-slate-500 text-center py-16">{{ t('common.loading') }}</div>

  <div v-else-if="animal">
    <!-- Header -->
    <div class="flex flex-wrap items-start gap-4 mb-6">
      <button class="btn-secondary btn-sm" @click="router.push('/animals')">← Tiere</button>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-3 flex-wrap">
          <h1 class="text-2xl font-bold text-slate-200">{{ animal.name }}</h1>
          <span class="badge-gray">{{ sexNotation(animal.sex) }}</span>
          <span v-if="!animal.is_active" class="badge-red">Inaktiv</span>
          <span v-if="animal.group_name" class="badge-blue">👥 {{ animal.group_name }}</span>
        </div>
        <p class="text-slate-400 italic">{{ animal.species }}<span v-if="animal.common_name"> · {{ animal.common_name }}</span></p>
        <p v-if="animal.morph" class="text-brand-400 text-sm">{{ animal.morph }}</p>
      </div>
      <div class="flex gap-2">
        <button class="btn-secondary btn-sm" @click="router.push(`/animals/${animal.id}/tree`)">🌳 {{ t('animal.tree') }}</button>
        <button class="btn-secondary btn-sm" @click="router.push(`/animals/${animal.id}/label`)">🏷 {{ t('animal.label') }}</button>
        <button class="btn-secondary btn-sm" @click="router.push(`/export?ids=${animal.id}`)">📜 {{ t('nav.herkunftsnachweis') }}</button>
        <button class="btn-secondary btn-sm" @click="router.push(`/animals/${animal.id}/edit`)">✏️ {{ t('common.edit') }}</button>
      </div>
    </div>

    <!-- Stats row -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      <div class="card text-center py-3">
        <div class="text-xl font-bold text-slate-200">{{ animal.weight_g ? `${animal.weight_g} g` : '—' }}</div>
        <div class="text-xs text-slate-500">{{ t('animal.weight').replace(' (g)','') }}</div>
      </div>
      <div class="card text-center py-3">
        <div class="text-xl font-bold text-slate-200">{{ animal.length_cm ? `${animal.length_cm} cm` : '—' }}</div>
        <div class="text-xs text-slate-500">{{ t('animal.length').replace(' (cm)','') }}</div>
      </div>
      <div class="card text-center py-3">
        <div class="text-xl font-bold text-slate-200">{{ age(animal.date_of_birth) ?? '—' }}</div>
        <div class="text-xs text-slate-500">{{ t('animal.age') }}</div>
      </div>
      <div class="card text-center py-3">
        <div class="text-xl font-bold" :class="animal.feeding_reminder_enabled === false ? 'text-slate-500' : 'text-slate-200'">
          {{ animal.feeding_reminder_enabled === false ? '—' : (animal.feeding_reminder_days ? `${animal.feeding_reminder_days}d` : t('animal.reminder_global')) }}
        </div>
        <div class="text-xs text-slate-500">{{ t('animal.feeding_reminder') }}</div>
      </div>
    </div>

    <!-- Parents -->
    <div v-if="animal.mother || animal.father" class="card mb-6">
      <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">{{ t('animal.parents') }}</h3>
      <div class="flex gap-4 flex-wrap">
        <div v-if="animal.mother" class="flex items-center gap-2 cursor-pointer hover:text-brand-400 transition-colors"
             @click="router.push(`/animals/${animal.mother.id}`)">
          <span class="text-slate-400 font-mono text-xs">0.1.0</span>
          <span class="text-sm">{{ animal.mother.name }}</span>
          <span class="text-xs text-slate-500">{{ animal.mother.morph ?? animal.mother.species }}</span>
        </div>
        <div v-if="animal.father" class="flex items-center gap-2 cursor-pointer hover:text-brand-400 transition-colors"
             @click="router.push(`/animals/${animal.father.id}`)">
          <span class="text-slate-400 font-mono text-xs">1.0.0</span>
          <span class="text-sm">{{ animal.father.name }}</span>
          <span class="text-xs text-slate-500">{{ animal.father.morph ?? animal.father.species }}</span>
        </div>
      </div>
    </div>

    <!-- Notes -->
    <div v-if="animal.notes" class="card mb-6 text-sm text-slate-400">{{ animal.notes }}</div>

    <!-- Haltungsbedingungen -->
    <div v-if="animal.temp_day_c || animal.humidity_min || animal.terrarium_size || animal.substrate" class="card mb-6">
      <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">🌡 {{ t('animal.husbandry') }}</h3>
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
        <div v-if="animal.temp_day_c || animal.temp_night_c" class="bg-surface-600 rounded-lg p-3">
          <div class="text-xs text-slate-500 mb-1">{{ t('animal.temp_day').replace(' (°C)','') }}</div>
          <div class="text-slate-200">
            <span v-if="animal.temp_day_c">🌤 {{ animal.temp_day_c }}°C</span>
            <span v-if="animal.temp_day_c && animal.temp_night_c" class="text-slate-500 mx-1">/</span>
            <span v-if="animal.temp_night_c">🌙 {{ animal.temp_night_c }}°C</span>
          </div>
        </div>
        <div v-if="animal.humidity_min || animal.humidity_max" class="bg-surface-600 rounded-lg p-3">
          <div class="text-xs text-slate-500 mb-1">{{ t('animal.humidity_min').replace(' (%)','') }}</div>
          <div class="text-slate-200">
            💧 {{ animal.humidity_min ?? '?' }}–{{ animal.humidity_max ?? '?' }}%
          </div>
        </div>
        <div v-if="animal.terrarium_size" class="bg-surface-600 rounded-lg p-3">
          <div class="text-xs text-slate-500 mb-1">{{ t('animal.terrarium') }}</div>
          <div class="text-slate-200">📦 {{ animal.terrarium_size }}</div>
        </div>
        <div v-if="animal.substrate" class="bg-surface-600 rounded-lg p-3">
          <div class="text-xs text-slate-500 mb-1">{{ t('animal.substrate') }}</div>
          <div class="text-slate-200">🌱 {{ animal.substrate }}</div>
        </div>
        <div v-if="animal.lighting_hours" class="bg-surface-600 rounded-lg p-3">
          <div class="text-xs text-slate-500 mb-1">{{ t('animal.lighting').replace(' (h/Tag)','').replace(' (h/day)','') }}</div>
          <div class="text-slate-200">💡 {{ animal.lighting_hours }}h</div>
        </div>
        <div v-if="animal.uv_required !== null && animal.uv_required !== undefined" class="bg-surface-600 rounded-lg p-3">
          <div class="text-xs text-slate-500 mb-1">UV</div>
          <div :class="animal.uv_required ? 'text-brand-400' : 'text-slate-400'">
            {{ animal.uv_required ? t('animal.uv') : '🚫 ' + t('common.no') + ' UV' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 mb-4 border-b border-surface-600">
      <button v-for="t in [{id:'feedings',label:t('feeding.title'),count:feedingList.length},{id:'sheddings',label:t('shedding.title'),count:sheddingList.length},{id:'custom',label:t('animal.custom_fields'),count:customFieldList.length}]"
        :key="t.id"
        @click="tab = t.id"
        :class="tab === t.id ? 'text-brand-400 border-b-2 border-brand-400' : 'text-slate-500 hover:text-slate-300'"
        class="px-4 py-2 text-sm font-medium transition-colors -mb-px">
        {{ t.label }} <span class="ml-1 text-xs opacity-60">({{ t.count }})</span>
      </button>
    </div>

    <!-- Feedings tab -->
    <div v-if="tab === 'feedings'">
      <div class="flex justify-between items-center mb-3">
        <span class="text-sm text-slate-500">{{ feedingList.length }} {{ t('common.entries') }}</span>
        <button class="btn-primary btn-sm" @click="showFeedingForm = !showFeedingForm">+ {{ t('feeding.add') }}</button>
      </div>

      <!-- Feeding form -->
      <div v-if="showFeedingForm" class="card mb-4">
        <h3 class="font-medium text-slate-200 mb-3">{{ t('feeding.add') }}</h3>
        <form @submit.prevent="addFeeding" class="grid sm:grid-cols-2 gap-3">
          <div><label>Datum & Zeit</label><input type="datetime-local" v-model="feedingForm.date" required /></div>
          <div><label>Futtertier</label><input v-model="feedingForm.food_type" placeholder="Maus, Ratte, Grillen…" required /></div>
          <div><label>{{ t('feeding.food_size') }}</label><input v-model="feedingForm.food_size" placeholder="Pinky, Adult, L…" /></div>
          <div><label>Anzahl</label><input type="number" v-model="feedingForm.food_count" min="1" /></div>
          <div><label>{{ t('feeding.weight') }}</label><input type="number" v-model="feedingForm.food_weight_g" step="0.1" min="0" /></div>
          <div class="flex gap-4 items-end pb-2">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="feedingForm.live" class="w-4 h-4" />Lebend
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="feedingForm.accepted" class="w-4 h-4" />Akzeptiert
            </label>
          </div>
          <div class="sm:col-span-2"><label>{{ t('feeding.notes') }}</label><textarea v-model="feedingForm.notes" rows="2" /></div>
          <div class="sm:col-span-2 flex gap-2">
            <button type="submit" class="btn-primary btn-sm" :disabled="savingFeeding">
              {{ savingFeeding ? t('common.saving') : t('common.save') }}
            </button>
            <button type="button" class="btn-secondary btn-sm" @click="showFeedingForm = false">Abbrechen</button>
          </div>
        </form>
      </div>

      <!-- Feeding list -->
      <div class="card">
        <div v-if="!feedingList.length" class="text-slate-500 text-center py-8">{{ t('feeding.noEntries') }}</div>
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="text-left text-slate-500 border-b border-surface-600">
              <th class="pb-2 pr-4">Datum</th>
              <th class="pb-2 pr-4">Futter</th>
              <th class="pb-2 pr-4">Status</th>
              <th class="pb-2 pr-4">Notiz</th>
              <th class="pb-2"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in feedingList" :key="f.id" class="table-row">
              <td class="py-2 pr-4 whitespace-nowrap text-slate-400">{{ fmtDateTime(f.date) }}</td>
              <td class="py-2 pr-4">
                <span class="text-slate-200">{{ f.food_count > 1 ? `${f.food_count}×` : '' }} {{ f.food_size }} {{ f.food_type }}</span>
                <span v-if="f.food_weight_g" class="text-slate-500 ml-1">· {{ f.food_weight_g }}g</span>
                <span v-if="f.live" class="badge-blue ml-1">Lebend</span>
              </td>
              <td class="py-2 pr-4">
                <span :class="f.accepted ? 'badge-green' : 'badge-red'">
                  {{ f.accepted ? t('feeding.accepted_label') : t('feeding.rejected_label') }}
                </span>
              </td>
              <td class="py-2 pr-4 text-slate-500 max-w-[150px] truncate">{{ f.notes }}</td>
              <td class="py-2">
                <button @click="deleteFeeding(f.id)" class="text-slate-600 hover:text-red-400 transition-colors">🗑</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Sheddings tab -->
    <div v-if="tab === 'sheddings'">
      <div class="flex justify-between items-center mb-3">
        <span class="text-sm text-slate-500">{{ sheddingList.length }} {{ t('common.entries') }}</span>
        <button class="btn-primary btn-sm" @click="showSheddingForm = !showSheddingForm">+ {{ t('shedding.add') }}</button>
      </div>

      <!-- Shedding form -->
      <div v-if="showSheddingForm" class="card mb-4">
        <h3 class="font-medium text-slate-200 mb-3">{{ t('shedding.add') }}</h3>
        <form @submit.prevent="addShedding" class="grid sm:grid-cols-2 gap-3">
          <div><label>Datum & Zeit</label><input type="datetime-local" v-model="sheddingForm.date" required /></div>
          <div><label>{{ t('shedding.pre_shed_days') }}</label><input type="number" v-model="sheddingForm.pre_shed_days" min="0" placeholder="7" /></div>
          <div class="flex gap-4 items-end pb-2">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="sheddingForm.complete" class="w-4 h-4" />{{ t('shedding.complete') }}
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="sheddingForm.in_one_piece" class="w-4 h-4" />{{ t('shedding.in_one_piece') }}
            </label>
          </div>
          <div class="sm:col-span-2"><label>{{ t('feeding.notes') }}</label><textarea v-model="sheddingForm.notes" rows="2" /></div>
          <div class="sm:col-span-2 flex gap-2">
            <button type="submit" class="btn-primary btn-sm" :disabled="savingShedding">
              {{ savingShedding ? t('common.saving') : t('common.save') }}
            </button>
            <button type="button" class="btn-secondary btn-sm" @click="showSheddingForm = false">Abbrechen</button>
          </div>
        </form>
      </div>

      <!-- Shedding list -->
      <div class="card">
        <div v-if="!sheddingList.length" class="text-slate-500 text-center py-8">{{ t('shedding.noEntries') }}</div>
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="text-left text-slate-500 border-b border-surface-600">
              <th class="pb-2 pr-4">Datum</th>
              <th class="pb-2 pr-4">Blauphase</th>
              <th class="pb-2 pr-4">Status</th>
              <th class="pb-2 pr-4">Notiz</th>
              <th class="pb-2"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in sheddingList" :key="s.id" class="table-row">
              <td class="py-2 pr-4 whitespace-nowrap text-slate-400">{{ fmtDateTime(s.date) }}</td>
              <td class="py-2 pr-4 text-slate-400">{{ s.pre_shed_days != null ? `${s.pre_shed_days} Tage` : '—' }}</td>
              <td class="py-2 pr-4">
                <span :class="s.complete ? 'badge-green' : 'badge-yellow'" class="mr-1">
                  {{ s.complete ? t('shedding.complete_label') : t('shedding.incomplete_label') }}
                </span>
                <span v-if="!s.in_one_piece" class="badge-red">Gerissen</span>
              </td>
              <td class="py-2 pr-4 text-slate-500 max-w-[150px] truncate">{{ s.notes }}</td>
              <td class="py-2">
                <button @click="deleteShedding(s.id)" class="text-slate-600 hover:text-red-400 transition-colors">🗑</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Custom fields tab -->
    <div v-if="tab === 'custom'">
      <div class="flex justify-between items-center mb-3">
        <span class="text-sm text-slate-500">Eigene Felder</span>
        <button class="btn-primary btn-sm" @click="showCfForm = !showCfForm">+ Feld</button>
      </div>

      <div v-if="showCfForm" class="card mb-4">
        <form @submit.prevent="addCustomField" class="grid sm:grid-cols-3 gap-3">
          <div><label>{{ t('animal.custom_fields') }}</label><input v-model="cfForm.field_name" required placeholder="e.g. Enclosure size" /></div>
          <div><label>{{ t('common.value') }}</label><input v-model="cfForm.field_value" placeholder="120×60×60 cm" /></div>
          <div>
            <label>Typ</label>
            <select v-model="cfForm.field_type">
              <option value="text">Text</option>
              <option value="number">Zahl</option>
              <option value="date">Datum</option>
              <option value="boolean">Ja/Nein</option>
            </select>
          </div>
          <div class="sm:col-span-3 flex gap-2">
            <button type="submit" class="btn-primary btn-sm" :disabled="savingCf">
              {{ savingCf ? t('common.saving') : t('common.add') }}
            </button>
            <button type="button" class="btn-secondary btn-sm" @click="showCfForm = false">Abbrechen</button>
          </div>
        </form>
      </div>

      <div class="card">
        <div v-if="!customFieldList.length" class="text-slate-500 text-center py-8">{{ t('animal.noAnimals') }}</div>
        <div v-for="cf in customFieldList" :key="cf.id"
             class="flex items-center justify-between py-2.5 border-b border-surface-600 last:border-0">
          <div>
            <span class="text-xs text-slate-500 uppercase tracking-wide">{{ cf.field_name }}</span>
            <div class="text-slate-200">{{ cf.field_value ?? '—' }}</div>
          </div>
          <button @click="deleteCustomField(cf.id)" class="text-slate-600 hover:text-red-400 transition-colors">🗑</button>
        </div>
      </div>
    </div>
  </div>
</template>
