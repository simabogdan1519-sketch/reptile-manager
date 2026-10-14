<script setup>
import { ref, onMounted } from 'vue'
import { breeding as breedingApi, animals as animalsApi } from '@/api'
import { bulk } from '@/api'
import { useI18n } from '@/i18n'
import { useRoute, useRouter } from 'vue-router'
import { fmtDate, sexNotation, sexBadge, errorMessage } from '@/utils/format'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const formError = ref('')
const bulkError = ref('')
const bulkDone = ref('')

const list = ref([])
const allAnimals = ref([])
const loading = ref(true)
const showForm = ref(route.query.new === '1')
const saving = ref(false)
const editId = ref(null)
const form = ref({
  female_id: '', male_id: '',
  date_paired: '', date_separated: '',
  copulation_observed: false,
  date_eggs_or_birth: '',
  clutch_size: '', fertile_count: '',
  success: null, notes: ''
})

onMounted(async () => {
  const [bRes, aRes] = await Promise.all([
    breedingApi.list({ limit: 200 }),
    animalsApi.list({ active_only: false, limit: 500 })
  ])
  list.value = bRes.data
  allAnimals.value = aRes.data
  loading.value = false
})

function resetForm() {
  form.value = { female_id: '', male_id: '', date_paired: '', date_separated: '', copulation_observed: false, date_eggs_or_birth: '', clutch_size: '', fertile_count: '', success: null, notes: '' }
  editId.value = null
  showForm.value = false
  formError.value = ''
}

async function save() {
  saving.value = true
  formError.value = ''
  try {
    const payload = { ...form.value, female_id: parseInt(form.value.female_id), male_id: parseInt(form.value.male_id) }
    if (!payload.date_paired) payload.date_paired = null
    if (!payload.date_separated) payload.date_separated = null
    if (!payload.date_eggs_or_birth) payload.date_eggs_or_birth = null
    if (!payload.clutch_size) payload.clutch_size = null
    if (!payload.fertile_count) payload.fertile_count = null

    if (editId.value) {
      const res = await breedingApi.update(editId.value, payload)
      const idx = list.value.findIndex(e => e.id === editId.value)
      if (idx !== -1) list.value[idx] = res.data
    } else {
      const res = await breedingApi.create(payload)
      list.value.unshift(res.data)
    }
    resetForm()
  } catch (e) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

function edit(event) {
  editId.value = event.id
  form.value = {
    female_id: event.female_id,
    male_id: event.male_id,
    date_paired: event.date_paired ?? '',
    date_separated: event.date_separated ?? '',
    copulation_observed: event.copulation_observed,
    date_eggs_or_birth: event.date_eggs_or_birth ?? '',
    clutch_size: event.clutch_size ?? '',
    fertile_count: event.fertile_count ?? '',
    success: event.success,
    notes: event.notes ?? ''
  }
  showForm.value = true
}

async function remove(id) {
  if (!confirm(t('breeding.confirmDelete'))) return
  await breedingApi.delete(id)
  list.value = list.value.filter(e => e.id !== id)
}


// Bulk offspring
const showBulkModal  = ref(false)
const bulkEvent      = ref(null)
const bulkQty        = ref(1)
const bulkDob        = ref(new Date().toISOString().slice(0, 10))
const bulkSex        = ref('unknown')
const bulkNotes      = ref('')
const savingBulk     = ref(false)

function openBulk(event) {
  bulkEvent.value = event
  showBulkModal.value = true
  bulkQty.value = 1
  bulkDob.value = new Date().toISOString().slice(0, 10)
  bulkSex.value = 'unknown'
  bulkNotes.value = ''
  bulkError.value = ''
}

async function createBulk() {
  if (!bulkEvent.value) return
  savingBulk.value = true
  try {
    const ev = bulkEvent.value
    const mother = allAnimals.value.find(a => a.id === ev.female_id)
    bulkError.value = ''
    await bulk.createAnimals(bulkQty.value, {
      name: t('breeding.offspring_name', { name: ev.female.name, year: new Date().getFullYear() }),
      group_id: mother?.group_id ?? null,
      species: ev.female.species,
      common_name: ev.female.common_name || null,
      sex: bulkSex.value,
      date_of_birth: bulkDob.value || null,
      origin: 'captive bred',
      mother_id: ev.female_id,
      father_id: ev.male_id,
      notes: bulkNotes.value || null,
      status: 'active',
    })
    showBulkModal.value = false
    bulkDone.value = t('breeding.bulk_done', { n: bulkQty.value })
    setTimeout(() => (bulkDone.value = ''), 5000)
  } catch (e) {
    bulkError.value = errorMessage(e)
  } finally {
    savingBulk.value = false
  }
}
const males   = () => allAnimals.value.filter(a => a.sex !== 'female')
const females = () => allAnimals.value.filter(a => a.sex !== 'male')

function outcome(e) {
  if (e.success === true)  return { cls: 'badge-green',  key: 'true' }
  if (e.success === false) return { cls: 'badge-red',    key: 'false' }
  return { cls: 'badge-yellow', key: 'null' }
}
</script>

<template>
  <div>
    <PageHeader :eyebrow="t('breeding.eyebrow')" :title="t('breeding.title')" :subtitle="t('common.n_entries', { n: list.length })">
      <template #actions>
        <button class="btn-primary" @click="showForm ? resetForm() : (showForm = true)">
          <Icon :name="showForm ? 'x' : 'plus'" :size="16" />{{ showForm ? t('common.cancel') : t('breeding.add') }}
        </button>
      </template>
    </PageHeader>

    <div v-if="bulkDone" class="alert-ok mb-4"><Icon name="check" :size="16" />{{ bulkDone }}
      <button class="link ml-auto" @click="router.push('/animals')">{{ t('animal.title') }} <Icon name="chevron" :size="14" /></button>
    </div>

    <!-- Form -->
    <form v-if="showForm" class="card mb-6 animate-rise" @submit.prevent="save">
      <h2 class="section-title mb-4">{{ editId ? t('breeding.edit') : t('breeding.add') }}</h2>
      <div v-if="formError" class="alert-error mb-4"><Icon name="alert" :size="16" />{{ formError }}</div>

      <div class="grid md:grid-cols-[1fr_auto_1fr] gap-3 items-end mb-5">
        <div>
          <label><span class="text-female">♀</span> {{ t('breeding.female') }} *</label>
          <select v-model="form.female_id" required>
            <option value="" disabled>{{ t('common.choose') }}</option>
            <option v-for="a in females()" :key="a.id" :value="a.id">{{ a.name }} · {{ a.morph ?? a.species }}</option>
          </select>
        </div>
        <div class="hidden md:grid place-items-center h-[38px] text-fg-faint font-display text-xl">×</div>
        <div>
          <label><span class="text-male">♂</span> {{ t('breeding.male') }} *</label>
          <select v-model="form.male_id" required>
            <option value="" disabled>{{ t('common.choose') }}</option>
            <option v-for="a in males()" :key="a.id" :value="a.id">{{ a.name }} · {{ a.morph ?? a.species }}</option>
          </select>
        </div>
      </div>

      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <div><label>{{ t('breeding.paired') }}</label><input type="date" v-model="form.date_paired" /></div>
        <div><label>{{ t('breeding.separated') }}</label><input type="date" v-model="form.date_separated" /></div>
        <div><label>{{ t('breeding.birth') }}</label><input type="date" v-model="form.date_eggs_or_birth" /></div>
        <div><label>{{ t('breeding.clutch_size') }}</label><input type="number" v-model="form.clutch_size" min="0" placeholder="8" class="num" /></div>
        <div><label>{{ t('breeding.fertile') }}</label><input type="number" v-model="form.fertile_count" min="0" class="num" /></div>
        <div>
          <label>{{ t('breeding.success') }}</label>
          <select v-model="form.success">
            <option :value="null">{{ t('breeding.successLabels.null') }}</option>
            <option :value="true">{{ t('breeding.successLabels.true') }}</option>
            <option :value="false">{{ t('breeding.successLabels.false') }}</option>
          </select>
        </div>
        <label class="option sm:col-span-2 lg:col-span-3" :class="{ on: form.copulation_observed }">
          <input type="checkbox" v-model="form.copulation_observed" /><span class="option-title">{{ t('breeding.copulation') }}</span>
        </label>
        <div class="sm:col-span-2 lg:col-span-3"><label>{{ t('breeding.notes') }}</label><textarea v-model="form.notes" rows="2" /></div>
      </div>
      <div class="flex gap-2 mt-4">
        <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? t('common.saving') : t('common.save') }}</button>
        <button type="button" class="btn-ghost" @click="resetForm">{{ t('common.cancel') }}</button>
      </div>
    </form>

    <!-- List -->
    <div v-if="loading" class="space-y-3"><div v-for="i in 3" :key="i" class="card h-36 animate-pulse" /></div>
    <div v-else-if="!list.length" class="card">
      <EmptyState icon="egg" :title="t('breeding.noEntries')" :text="t('breeding.empty_text')" />
    </div>
    <div v-else class="grid lg:grid-cols-2 gap-4 stagger">
      <article v-for="e in list" :key="e.id" class="card">
        <div class="flex items-start justify-between gap-3 mb-4">
          <span :class="outcome(e).cls"><span class="dot" />{{ t('breeding.successLabels.' + outcome(e).key) }}</span>
          <div class="flex gap-1 -mr-2 -mt-1">
            <button class="icon-btn" :title="t('breeding.addOffspring')" @click="openBulk(e)"><Icon name="hatch" :size="16" /></button>
            <button class="icon-btn" :title="t('common.edit')" @click="edit(e)"><Icon name="edit" :size="16" /></button>
            <button class="icon-btn danger" :title="t('common.delete')" @click="remove(e.id)"><Icon name="trash" :size="16" /></button>
          </div>
        </div>

        <!-- Pair -->
        <div class="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
          <button class="tile text-left hover:border-female/40 transition-colors min-w-0" @click="router.push(`/animals/${e.female_id}`)">
            <span :class="sexBadge('female')">{{ sexNotation('female') }}</span>
            <div class="font-display font-semibold text-fg mt-1.5 truncate">{{ e.female.name }}</div>
            <div class="text-[11.5px] text-fg-faint truncate">{{ e.female.morph || e.female.species }}</div>
          </button>
          <span class="font-display text-2xl text-fg-faint">×</span>
          <button class="tile text-left hover:border-male/40 transition-colors min-w-0" @click="router.push(`/animals/${e.male_id}`)">
            <span :class="sexBadge('male')">{{ sexNotation('male') }}</span>
            <div class="font-display font-semibold text-fg mt-1.5 truncate">{{ e.male.name }}</div>
            <div class="text-[11.5px] text-fg-faint truncate">{{ e.male.morph || e.male.species }}</div>
          </button>
        </div>

        <!-- Timeline -->
        <ol class="grid grid-cols-3 gap-2 mt-5 relative">
          <span class="absolute left-[8%] right-[8%] top-[5px] h-px bg-line" />
          <li v-for="step in [
                { k: 'paired', d: e.date_paired },
                { k: 'separated', d: e.date_separated },
                { k: 'birth_short', d: e.date_eggs_or_birth },
              ]" :key="step.k" class="relative text-center">
            <span class="relative z-10 block mx-auto w-[11px] h-[11px] rounded-full border-2"
                  :class="step.d ? 'bg-moss-400 border-moss-400' : 'bg-ink-900 border-line-strong'" />
            <div class="eyebrow mt-2 !tracking-[0.12em]">{{ t('breeding.' + step.k) }}</div>
            <div class="text-[13px] mt-0.5 num" :class="step.d ? 'text-fg' : 'text-fg-faint'">{{ fmtDate(step.d) }}</div>
          </li>
        </ol>

        <div class="flex flex-wrap items-center gap-x-5 gap-y-1 mt-4 pt-4 border-t border-line text-[13px]">
          <span class="text-fg-muted">{{ t('breeding.clutch_size') }}: <b class="text-fg num">{{ e.clutch_size ?? '—' }}</b></span>
          <span class="text-fg-muted">{{ t('breeding.fertile') }}: <b class="text-fg num">{{ e.fertile_count ?? '—' }}</b></span>
          <span v-if="e.copulation_observed" class="badge-gray"><Icon name="check" :size="12" />{{ t('breeding.copulation_short') }}</span>
        </div>
        <p v-if="e.notes" class="text-[13px] text-fg-muted mt-3 whitespace-pre-line">{{ e.notes }}</p>
      </article>
    </div>

    <!-- Bulk offspring -->
    <Modal :open="showBulkModal" :title="t('breeding.addOffspring')" icon="hatch" @close="showBulkModal = false">
      <p v-if="bulkEvent" class="text-sm text-fg-muted mb-4">
        {{ bulkEvent.female.name }} × {{ bulkEvent.male.name }} · <span class="italic">{{ bulkEvent.female.species }}</span>
      </p>
      <div v-if="bulkError" class="alert-error mb-4"><Icon name="alert" :size="16" />{{ bulkError }}</div>
      <div class="space-y-4">
        <div>
          <label>{{ t('breeding.quantity') }}</label>
          <input type="number" v-model.number="bulkQty" min="1" max="500" class="num" />
          <p class="hint">{{ t('breeding.bulk_hint') }}</p>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label>{{ t('animal.dob') }}</label><input type="date" v-model="bulkDob" /></div>
          <div>
            <label>{{ t('animal.sex') }}</label>
            <select v-model="bulkSex">
              <option value="unknown">{{ t('animal.sexes.unknown') }}</option>
              <option value="male">{{ t('animal.sexes.male') }}</option>
              <option value="female">{{ t('animal.sexes.female') }}</option>
            </select>
          </div>
        </div>
        <div><label>{{ t('breeding.notes') }}</label><textarea v-model="bulkNotes" rows="2" :placeholder="t('breeding.bulk_notes_ph')" /></div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showBulkModal = false">{{ t('common.cancel') }}</button>
        <button class="btn-primary" :disabled="savingBulk" @click="createBulk">
          {{ savingBulk ? t('common.saving') : t('breeding.bulk_create', { n: bulkQty }) }}
        </button>
      </template>
    </Modal>
  </div>
</template>
