<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '@/i18n'
import { animals as animalsApi, groups as groupsApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { mediaUrl } from '@/utils/media'
import { errorMessage } from '@/utils/format'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'

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
    } catch { error.value = t('animal.load_error') }
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
    error.value = errorMessage(e)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-4xl">
    <PageHeader :eyebrow="isEdit ? form.name || t('animal.title') : t('animal.eyebrow')"
                :title="isEdit ? t('animal.edit') : t('animal.add')" back @back="router.back()" />

    <div v-if="loading" class="card h-96 animate-pulse" />

    <form v-else class="space-y-4 pb-24" @submit.prevent="save">
      <div v-if="error" class="alert-error"><Icon name="alert" :size="16" class="mt-0.5" />{{ error }}</div>

      <!-- Identity -->
      <section class="form-section">
        <div class="form-aside">
          <h2 class="section-title">{{ t('animal.sec_identity') }}</h2>
          <p class="hint">{{ t('animal.sec_identity_hint') }}</p>
        </div>
        <div class="grid sm:grid-cols-2 gap-4">
          <div><label>{{ t('animal.name') }} *</label><input v-model="form.name" required :placeholder="t('animal.name_ph')" /></div>
          <div>
            <label>{{ t('animal.sex') }}</label>
            <div class="seg w-full h-[38px] items-center">
              <button v-for="sx in ['male','female','unknown']" :key="sx" type="button" class="flex-1"
                      :class="{ on: form.sex === sx }" @click="form.sex = sx">{{ t('animal.sexes.' + sx) }}</button>
            </div>
          </div>
          <div><label>{{ t('animal.species') }} *</label><input v-model="form.species" required placeholder="Python regius" class="italic" /></div>
          <div><label>{{ t('animal.common_name') }}</label><input v-model="form.common_name" :placeholder="t('animal.common_name_ph')" /></div>
          <div class="sm:col-span-2"><label>{{ t('animal.morph') }}</label><input v-model="form.morph" :placeholder="t('animal.morph_ph')" /></div>
          <div>
            <label>{{ t('animal.tracking_id') }}</label>
            <input v-model="form.tracking_id" :placeholder="t('animal.tracking_auto')" class="num" />
          </div>
          <div>
            <label>{{ t('animal.status') }}</label>
            <div class="seg w-full h-[38px] items-center">
              <button v-for="st in ['active','inactive','sold']" :key="st" type="button" class="flex-1"
                      :class="{ on: form.status === st }" @click="form.status = st">{{ t('status.' + st) }}</button>
            </div>
          </div>
          <div v-if="groupOptions.length || auth.isAdmin" class="sm:col-span-2">
            <label>{{ t('access.group') }}{{ auth.isAdmin ? '' : ' *' }}</label>
            <select v-model="form.group_id" :required="!auth.isAdmin">
              <option :value="null" :disabled="!auth.isAdmin">{{ auth.isAdmin ? t('access.no_group') : t('access.choose_group') }}</option>
              <option v-for="g in groupOptions" :key="g.id" :value="g.id">{{ g.name }}</option>
            </select>
            <p class="hint">{{ t('access.group_hint') }}</p>
          </div>
        </div>
      </section>

      <!-- Photo -->
      <section class="form-section">
        <div class="form-aside">
          <h2 class="section-title">{{ t('animal.photo') }}</h2>
          <p class="hint">{{ t('animal.photo_hint') }}</p>
        </div>
        <div class="flex gap-4 items-start">
          <div class="w-28 h-28 rounded-xl bg-ink-850 flex-shrink-0 overflow-hidden grid place-items-center border border-line-strong">
            <img v-if="photoPreview || form.photo_url" :src="photoPreview || mediaUrl(form.photo_url)" class="w-full h-full object-cover" />
            <Icon v-else name="image" :size="30" :stroke="1.3" class="text-fg-faint" />
          </div>
          <div class="flex-1 min-w-0 space-y-3">
            <input type="file" accept="image/*" @change="onPhotoSelect" />
            <div class="flex flex-wrap gap-2">
              <button v-if="photoPreview" type="button" class="btn-ghost btn-sm" @click="removePhoto"><Icon name="x" :size="14" />{{ t('animal.photo_discard') }}</button>
              <button v-else-if="isUploadedPhoto" type="button" class="btn-danger btn-sm" @click="removePhoto"><Icon name="trash" :size="14" />{{ t('animal.photo_remove') }}</button>
            </div>
            <div v-if="!isUploadedPhoto">
              <label>{{ t('animal.photo_url') }}</label>
              <input v-model="form.photo_url" type="url" placeholder="https://…" />
            </div>
          </div>
        </div>
      </section>

      <!-- Origin & measurements -->
      <section class="form-section">
        <div class="form-aside">
          <h2 class="section-title">{{ t('animal.sec_history') }}</h2>
          <p class="hint">{{ t('animal.sec_history_hint') }}</p>
        </div>
        <div class="grid sm:grid-cols-2 gap-4">
          <div><label>{{ t('animal.dob') }}</label><input type="date" v-model="form.date_of_birth" /></div>
          <div><label>{{ t('animal.acquired') }}</label><input type="date" v-model="form.date_acquired" /></div>
          <div class="sm:col-span-2">
            <label>{{ t('animal.origin') }}</label>
            <select v-model="form.origin">
              <option value="">{{ t('animal.origins.none') }}</option>
              <option value="captive bred">{{ t('animal.origins.cb') }}</option>
              <option value="wild caught">{{ t('animal.origins.wc') }}</option>
              <option value="farm bred">{{ t('animal.origins.fb') }}</option>
              <option value="imported">{{ t('animal.origins.imported') }}</option>
            </select>
          </div>
          <div><label>{{ t('animal.weight') }}</label><input type="number" v-model="form.weight_g" step="0.1" min="0" placeholder="1200" class="num" /></div>
          <div><label>{{ t('animal.length') }}</label><input type="number" v-model="form.length_cm" step="0.1" min="0" placeholder="120" class="num" /></div>
          <div>
            <label>{{ t('animal.mother') }}</label>
            <select v-model="form.mother_id">
              <option :value="null">{{ t('common.none') }}</option>
              <option v-for="a in parentOptions.filter(a => a.sex !== 'male')" :key="a.id" :value="a.id">{{ a.name }} · {{ a.species }}</option>
            </select>
          </div>
          <div>
            <label>{{ t('animal.father') }}</label>
            <select v-model="form.father_id">
              <option :value="null">{{ t('common.none') }}</option>
              <option v-for="a in parentOptions.filter(a => a.sex !== 'female')" :key="a.id" :value="a.id">{{ a.name }} · {{ a.species }}</option>
            </select>
          </div>
        </div>
      </section>

      <!-- Husbandry -->
      <section class="form-section">
        <div class="form-aside">
          <h2 class="section-title">{{ t('animal.husbandry') }}</h2>
          <p class="hint">{{ t('animal.sec_husbandry_hint') }}</p>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div><label>{{ t('animal.temp_day') }}</label><input type="number" v-model="form.temp_day_c" step="0.5" placeholder="32" class="num" /></div>
          <div><label>{{ t('animal.temp_night') }}</label><input type="number" v-model="form.temp_night_c" step="0.5" placeholder="24" class="num" /></div>
          <div><label>{{ t('animal.humidity_min') }}</label><input type="number" v-model="form.humidity_min" min="0" max="100" placeholder="50" class="num" /></div>
          <div><label>{{ t('animal.humidity_max') }}</label><input type="number" v-model="form.humidity_max" min="0" max="100" placeholder="70" class="num" /></div>
          <div><label>{{ t('animal.terrarium') }}</label><input v-model="form.terrarium_size" placeholder="120×60×60 cm" /></div>
          <div><label>{{ t('animal.substrate') }}</label><input v-model="form.substrate" :placeholder="t('animal.substrate_ph')" /></div>
          <div><label>{{ t('animal.lighting') }}</label><input type="number" v-model="form.lighting_hours" min="0" max="24" placeholder="12" class="num" /></div>
          <div class="flex items-end">
            <label class="option w-full" :class="{ on: form.uv_required === true }">
              <input type="checkbox" :checked="form.uv_required === true" @change="form.uv_required = $event.target.checked" />
              <span class="option-title">{{ t('animal.uv') }}</span>
            </label>
          </div>
        </div>
      </section>

      <!-- Reminder -->
      <section class="form-section">
        <div class="form-aside">
          <h2 class="section-title">{{ t('animal.feeding_reminder') }}</h2>
          <p class="hint">{{ t('animal.sec_reminder_hint') }}</p>
        </div>
        <div class="grid sm:grid-cols-2 gap-4 items-end">
          <label class="option" :class="{ on: form.feeding_reminder_enabled }">
            <input type="checkbox" v-model="form.feeding_reminder_enabled" />
            <span><span class="option-title block">{{ t('animal.reminder_active') }}</span><span class="option-desc block">{{ t('animal.reminder_desc') }}</span></span>
          </label>
          <div>
            <label>{{ t('animal.reminder_days') }}</label>
            <input type="number" v-model="form.feeding_reminder_days" min="1" max="365" class="num"
                   :disabled="!form.feeding_reminder_enabled" :placeholder="t('animal.reminder_global')" />
          </div>
        </div>
      </section>

      <!-- Notes -->
      <section class="form-section">
        <div class="form-aside"><h2 class="section-title">{{ t('animal.notes') }}</h2></div>
        <textarea v-model="form.notes" rows="4" :placeholder="t('animal.notes_ph')" />
      </section>

      <!-- Sticky actions -->
      <div class="fixed bottom-0 inset-x-0 lg:left-[264px] z-20 border-t border-line bg-ink-950/85 backdrop-blur-md">
        <div class="max-w-4xl mx-auto lg:mx-10 px-4 sm:px-6 py-3 flex items-center justify-end gap-2">
          <button type="button" class="btn-ghost" @click="router.back()">{{ t('common.cancel') }}</button>
          <button type="submit" class="btn-primary min-w-[120px]" :disabled="saving">
            <Icon v-if="!saving" name="check" :size="16" />{{ saving ? t('common.saving') : t('common.save') }}
          </button>
        </div>
      </div>
    </form>
  </div>
</template>

<style scoped>
.form-section { @apply card grid md:grid-cols-[220px_1fr] gap-5 md:gap-8; }
.form-aside { @apply md:pt-1; }
</style>
