<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '@/i18n'
import { animals as animalsApi, groups as groupsApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { mediaUrl } from '@/utils/media'

const route  = useRoute()
const router = useRouter()
const { t }  = useI18n()
const auth   = useAuthStore()
const groupOptions = ref([])

const isEdit  = computed(() => !!route.params.id && route.params.id !== 'new')
const loading = ref(false)
const saving  = ref(false)
const error   = ref('')
const allAnimals   = ref([])
const photoFile    = ref(null)
const photoPreview = ref(null)

const form = ref({
  name: '', species: '', common_name: '', morph: '',
  sex: 'unknown', date_of_birth: '', date_acquired: '',
  origin: '', weight_g: '', length_cm: '',
  photo_url: null, notes: '',
  status: 'active', tracking_id: '',
  mother_id: null, father_id: null,
  feeding_reminder_enabled: true, feeding_reminder_days: null,
  temp_day_c: '', temp_night_c: '', humidity_min: '', humidity_max: '',
  terrarium_size: '', substrate: '', uv_required: null, lighting_hours: '',
  group_id: null,
})

const parentOptions = computed(() => {
  const selfId = isEdit.value ? parseInt(route.params.id) : null
  return allAnimals.value.filter(a => a.id !== selfId)
})

const isUploadedPhoto = computed(() =>
  form.value.photo_url && form.value.photo_url.startsWith('/uploads/')
)

onMounted(async () => {
  try {
    groupOptions.value = (await groupsApi.list()).data
    if (!isEdit.value && !auth.isAdmin && groupOptions.value.length === 1)
      form.value.group_id = groupOptions.value[0].id
  } catch { /* non-critical */ }
  try {
    const res = await animalsApi.list({ active_only: false, limit: 500 })
    allAnimals.value = res.data
  } catch { /* non-critical */ }

  if (isEdit.value) {
    loading.value = true
    try {
      const { data } = await animalsApi.get(route.params.id)
      Object.keys(form.value).forEach(k => {
        if (data[k] !== undefined && data[k] !== null) form.value[k] = data[k]
      })
      if (data.date_of_birth) form.value.date_of_birth = data.date_of_birth.substring(0, 10)
      if (data.date_acquired) form.value.date_acquired  = data.date_acquired.substring(0, 10)
    } catch { error.value = 'Tier konnte nicht geladen werden.' }
    finally { loading.value = false }
  }
})

function onPhotoSelect(e) {
  const file = e.target.files[0]
  if (!file) return
  photoFile.value   = file
  photoPreview.value = URL.createObjectURL(file)
}

function removePhoto() {
  form.value.photo_url = null
  photoFile.value      = null
  photoPreview.value   = null
}

async function save() {
  error.value = ''
  saving.value = true
  try {
    const payload = { ...form.value }
    ;['weight_g','length_cm','date_of_birth','date_acquired','common_name','morph',
      'origin','notes','tracking_id'].forEach(k => {
      if (payload[k] === '') payload[k] = null
    })
    ;['weight_g','length_cm'].forEach(k => {
      if (payload[k] !== null) payload[k] = parseFloat(payload[k]) || null
    })
    if (!payload.feeding_reminder_days) payload.feeding_reminder_days = null
    ;['temp_day_c','temp_night_c','humidity_min','humidity_max','lighting_hours'].forEach(k => {
      payload[k] = payload[k] === '' || payload[k] === null ? null : parseFloat(payload[k]) || null
    })
    ;['terrarium_size','substrate'].forEach(k => {
      if (payload[k] === '') payload[k] = null
    })
    payload.is_active = payload.status === 'active'

    let savedId
    if (isEdit.value) {
      await animalsApi.update(route.params.id, payload)
      savedId = route.params.id
    } else {
      const res = await animalsApi.create(payload)
      savedId = res.data.id
    }

    if (photoFile.value) {
      try { await animalsApi.uploadPhoto(savedId, photoFile.value) } catch { /* non-critical */ }
    }

    router.push(`/animals/${savedId}`)
  } catch (e) {
    const d = e.response?.data?.detail
    error.value = Array.isArray(d) ? d.map(x => x.msg).join(', ') : (d || e.message || 'Unbekannter Fehler')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl">
    <div class="flex items-center gap-3 mb-6">
      <button class="btn-secondary btn-sm" @click="router.back()">{{ t('common.back') }}</button>
      <h1 class="text-xl md:text-2xl font-bold text-slate-200">
        {{ isEdit ? t('animal.edit') : t('animal.add') }}
      </h1>
    </div>

    <div v-if="loading" class="text-slate-500 text-center py-16">{{ t('common.loading') }}</div>

    <form v-else @submit.prevent="save" class="card space-y-5">

      <div v-if="error" class="bg-red-900/40 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm">⚠ {{ error }}</div>

      <!-- Basic info -->
      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label>{{ t('animal.name') }} *</label>
          <input v-model="form.name" required placeholder="z.B. Noodle" />
        </div>
        <div>
          <label>{{ t('animal.sex') }}</label>
          <select v-model="form.sex">
            <option value="unknown">{{ t('animal.sexes.unknown') }}</option>
            <option value="male">{{ t('animal.sexes.male') }}</option>
            <option value="female">{{ t('animal.sexes.female') }}</option>
          </select>
        </div>
        <div>
          <label>{{ t('animal.species') }} *</label>
          <input v-model="form.species" required placeholder="Python regius" />
        </div>
        <div>
          <label>{{ t('animal.common_name') }}</label>
          <input v-model="form.common_name" placeholder="Königspython" />
        </div>
        <div class="sm:col-span-2">
          <label>{{ t('animal.morph') }}</label>
          <input v-model="form.morph" placeholder="z.B. Pastel Clown…" />
        </div>
      </div>

      <!-- Tracking ID + Status -->
      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label>{{ t('animal.tracking_id') }}</label>
          <input v-model="form.tracking_id" placeholder="Automatisch vergeben wenn leer" />
          <p class="text-xs text-slate-600 mt-1">Leer lassen = nächste freie Nummer</p>
        </div>
        <div>
          <label>{{ t('animal.status') }}</label>
          <div class="flex gap-2 mt-1">
            <button v-for="s in ['active','inactive','sold']" :key="s" type="button"
              class="flex-1 py-1.5 rounded-lg text-sm font-medium border transition-all"
              :class="form.status === s
                ? s === 'active'   ? 'bg-brand-600 border-brand-500 text-white'
                : s === 'sold'     ? 'bg-purple-700 border-purple-500 text-white'
                :                    'bg-slate-600 border-slate-500 text-white'
                : 'bg-surface-600 border-surface-500 text-slate-400 hover:text-slate-200'"
              @click="form.status = s">
              {{ t(`status.${s}`) }}
            </button>
          </div>
        </div>
      </div>

      <!-- Access group -->
      <div v-if="groupOptions.length || auth.isAdmin">
        <label>👥 {{ t('access.group') }}{{ auth.isAdmin ? '' : ' *' }}</label>
        <select v-model="form.group_id" :required="!auth.isAdmin">
          <option :value="null" :disabled="!auth.isAdmin">
            {{ auth.isAdmin ? t('access.no_group') : t('access.choose_group') }}
          </option>
          <option v-for="g in groupOptions" :key="g.id" :value="g.id">{{ g.name }}</option>
        </select>
        <p class="text-xs text-slate-600 mt-1">{{ t('access.group_hint') }}</p>
      </div>

      <hr class="border-surface-500" />

      <!-- Dates & origin -->
      <div class="grid sm:grid-cols-2 gap-4">
        <div><label>{{ t('animal.dob') }}</label><input type="date" v-model="form.date_of_birth" /></div>
        <div><label>{{ t('animal.acquired') }}</label><input type="date" v-model="form.date_acquired" /></div>
        <div>
          <label>{{ t('animal.origin') }}</label>
          <select v-model="form.origin">
            <option value="">{{ t('animal.origins.none') }}</option>
            <option value="captive bred">{{ t('animal.origins.cb') }}</option>
            <option value="wild caught">{{ t('animal.origins.wc') }}</option>
            <option value="farm bred">{{ t('animal.origins.fb') }}</option>
            <option value="imported">{{ t('animal.origins.imported') }}</option>
          </select>
        </div>
      </div>

      <hr class="border-surface-500" />

      <!-- Measurements -->
      <div class="grid sm:grid-cols-2 gap-4">
        <div><label>{{ t('animal.weight') }}</label><input type="number" v-model="form.weight_g" step="0.1" min="0" placeholder="1200" /></div>
        <div><label>{{ t('animal.length') }}</label><input type="number" v-model="form.length_cm" step="0.1" min="0" placeholder="120" /></div>
      </div>

      <hr class="border-surface-500" />

      <!-- Parents -->
      <div>
        <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">{{ t('animal.parents') }}</h3>
        <div class="grid sm:grid-cols-2 gap-4">
          <div>
            <label>{{ t('animal.mother') }}</label>
            <select v-model="form.mother_id">
              <option :value="null">— keine —</option>
              <option v-for="a in parentOptions.filter(a => a.sex !== 'male')" :key="a.id" :value="a.id">
                {{ a.name }} ({{ a.species }})
              </option>
            </select>
          </div>
          <div>
            <label>{{ t('animal.father') }}</label>
            <select v-model="form.father_id">
              <option :value="null">— keine —</option>
              <option v-for="a in parentOptions.filter(a => a.sex !== 'female')" :key="a.id" :value="a.id">
                {{ a.name }} ({{ a.species }})
              </option>
            </select>
          </div>
        </div>
      </div>

      <hr class="border-surface-500" />

      <!-- Feeding reminder -->
      <div>
        <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">{{ t('animal.feeding_reminder') }}</h3>
        <div class="flex flex-wrap gap-5 items-end">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="form.feeding_reminder_enabled" class="w-4 h-4" />
            <span class="text-sm text-slate-300">{{ t('animal.reminder_active') }}</span>
          </label>
          <div class="flex-1 min-w-[160px]">
            <label>{{ t('animal.reminder_days') }}</label>
            <input type="number" v-model="form.feeding_reminder_days" min="1" max="365"
                   :disabled="!form.feeding_reminder_enabled"
                   :placeholder="t('animal.reminder_global')" />
          </div>
        </div>
      </div>

      <hr class="border-surface-500" />

      <!-- Husbandry -->
      <div>
        <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">🌡 {{ t('animal.husbandry') }}</h3>
        <div class="grid sm:grid-cols-2 gap-4">
          <div><label>{{ t('animal.temp_day') }}</label><input type="number" v-model="form.temp_day_c" step="0.5" placeholder="28" /></div>
          <div><label>{{ t('animal.temp_night') }}</label><input type="number" v-model="form.temp_night_c" step="0.5" placeholder="22" /></div>
          <div><label>{{ t('animal.humidity_min') }}</label><input type="number" v-model="form.humidity_min" min="0" max="100" placeholder="60" /></div>
          <div><label>{{ t('animal.humidity_max') }}</label><input type="number" v-model="form.humidity_max" min="0" max="100" placeholder="80" /></div>
          <div><label>{{ t('animal.terrarium') }}</label><input v-model="form.terrarium_size" placeholder="120×60×60 cm" /></div>
          <div><label>{{ t('animal.substrate') }}</label><input v-model="form.substrate" placeholder="Kokoserde…" /></div>
          <div><label>{{ t('animal.lighting') }}</label><input type="number" v-model="form.lighting_hours" min="0" max="24" placeholder="12" /></div>
          <div class="flex items-end pb-2">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" class="w-4 h-4"
                     :checked="form.uv_required === true"
                     @change="form.uv_required = $event.target.checked" />
              <span class="text-sm text-slate-300">{{ t('animal.uv') }}</span>
            </label>
          </div>
        </div>
      </div>

      <hr class="border-surface-500" />

      <!-- Photo -->
      <div>
        <label class="mb-2 block">{{ t('animal.photo') }}</label>
        <div class="flex gap-4 items-start">
          <div class="w-20 h-20 rounded-lg bg-surface-600 flex-shrink-0 overflow-hidden
                      flex items-center justify-center border border-surface-500">
            <img v-if="photoPreview || form.photo_url"
                 :src="photoPreview || mediaUrl(form.photo_url)"
                 class="w-full h-full object-cover" />
            <span v-else class="text-3xl opacity-30">🦎</span>
          </div>
          <div class="flex-1 space-y-2">
            <!-- Existing uploaded photo -->
            <div v-if="isUploadedPhoto && !photoPreview"
                 class="flex items-center gap-2 text-sm text-slate-400">
              <span>📷 Hochgeladenes Foto</span>
              <button type="button" @click="removePhoto"
                      class="text-xs text-red-400 hover:text-red-300">🗑 Entfernen</button>
            </div>
            <!-- File upload -->
            <div>
              <label class="text-xs text-slate-500 mb-1">Neues Foto hochladen</label>
              <input type="file" accept="image/*" @change="onPhotoSelect"
                     class="file:btn-secondary file:btn-sm file:mr-2 file:cursor-pointer text-sm" />
              <button v-if="photoPreview" type="button" @click="removePhoto"
                      class="text-xs text-red-400 hover:text-red-300 mt-1 block">✕ Auswahl verwerfen</button>
            </div>
            <!-- External URL (only if no uploaded photo) -->
            <div v-if="!isUploadedPhoto">
              <label class="text-xs text-slate-500">Oder externe URL:</label>
              <input v-model="form.photo_url" type="url" placeholder="https://…" class="text-sm mt-1" />
            </div>
          </div>
        </div>
      </div>

      <!-- Notes -->
      <div>
        <label>{{ t('animal.notes') }}</label>
        <textarea v-model="form.notes" rows="3" placeholder="Besonderheiten, Herkunft…"></textarea>
      </div>

      <!-- Actions -->
      <div class="flex gap-3 pt-2">
        <button type="submit" class="btn-primary" :disabled="saving">
          {{ saving ? t('common.saving') : t('common.save') }}
        </button>
        <button type="button" class="btn-secondary" @click="router.back()">{{ t('common.cancel') }}</button>
      </div>
    </form>
  </div>
</template>
