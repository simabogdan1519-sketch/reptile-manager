<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from '@/i18n'
import { animals as animalsApi, exportApi, buildBaseURL } from '@/api'
import { sexNotation, sexBadge } from '@/utils/format'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import AnimalAvatar from '@/components/AnimalAvatar.vue'

const { t }  = useI18n()
const route  = useRoute()

const allAnimals      = ref([])
const filteredAnimals = ref([])
const loading         = ref(true)
const genInv          = ref(false)
const genHkn          = ref(false)
const exportError     = ref('')

const selectedIds   = ref([])
const buyer         = ref({ name: '', street: '', zip_city: '', phone: '' })
const originType    = ref('nachzucht')
const citesNr       = ref('')
const einfuhrNr     = ref('')
const sonstigesText = ref('')
const ort           = ref('')
const blanko        = ref(false)
const searchTerm    = ref('')

onMounted(async () => {
  try {
    const res = await animalsApi.list({ active_only: true, limit: 500 })
    allAnimals.value      = res.data
    filteredAnimals.value = res.data
    if (route.query.ids) {
      selectedIds.value = String(route.query.ids).split(',').map(Number).filter(Boolean)
    }
  } finally {
    loading.value = false
  }
})

function applySearch() {
  const q = searchTerm.value.toLowerCase()
  filteredAnimals.value = q
    ? allAnimals.value.filter(a =>
        a.name.toLowerCase().includes(q) ||
        a.species.toLowerCase().includes(q) ||
        (a.morph || '').toLowerCase().includes(q))
    : allAnimals.value
}

function toggleAnimal(id) {
  const i = selectedIds.value.indexOf(id)
  if (i >= 0) selectedIds.value.splice(i, 1)
  else selectedIds.value.push(id)
}

function getDownloadUrl(path) {
  const base  = buildBaseURL().replace(/\/api\/?$/, '/api')
  const token = localStorage.getItem('access_token') || ''
  return `${base}${path}?token=${encodeURIComponent(token)}`
}

async function downloadInventory() {
  genInv.value = true
  const a = document.createElement('a')
  a.href = getDownloadUrl('/export/inventory')
  a.target = '_blank'
  a.rel = 'noopener'
  document.body.appendChild(a); a.click(); document.body.removeChild(a)
  setTimeout(() => { genInv.value = false }, 1500)
}

async function downloadHkn() {
  exportError.value = ''
  if (!selectedIds.value.length) {
    exportError.value = t('export.select_hint')
    return
  }
  genHkn.value = true
  try {
    const res = await exportApi.herkunftsnachweis({
      animal_ids:     selectedIds.value,
      buyer_name:     blanko.value ? '' : buyer.value.name,
      buyer_street:   blanko.value ? '' : buyer.value.street,
      buyer_zip_city: blanko.value ? '' : buyer.value.zip_city,
      buyer_phone:    blanko.value ? '' : buyer.value.phone,
      origin_type:    originType.value,
      cites_nr:       citesNr.value,
      einfuhr_nr:     einfuhrNr.value,
      sonstiges_text: sonstigesText.value,
      ort_datum:      blanko.value ? '' : ort.value,
      blanko:         blanko.value,
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url
    a.download = `${t('export.filename')}${blanko.value ? '_blank' : ''}_${new Date().toISOString().slice(0,10)}.pdf`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 2000)
  } catch (e) {
    if (e.response?.data instanceof Blob) {
      const text = await e.response.data.text()
      try { exportError.value = JSON.parse(text)?.detail || text } catch { exportError.value = text }
    } else {
      exportError.value = `HTTP ${e.response?.status || t('common.network_error')}: ${e.message}`
    }
  } finally { genHkn.value = false }
}


</script>

<template>
  <div>
    <PageHeader :eyebrow="t('export.eyebrow')" :title="t('export.title')" :subtitle="t('export.subtitle')" />

    <!-- Inventory -->
    <section class="card mb-5 flex flex-col sm:flex-row sm:items-center gap-4 animate-rise">
      <span class="w-11 h-11 rounded-xl bg-lagoon-400/10 border border-lagoon-400/25 text-lagoon-400 grid place-items-center flex-shrink-0">
        <Icon name="sheet" :size="20" />
      </span>
      <div class="flex-1 min-w-0">
        <h2 class="font-display font-semibold text-fg text-[17px]">{{ t('export.inventory_title') }}</h2>
        <p class="text-sm text-fg-muted mt-0.5">{{ t('export.inventory_desc') }}</p>
      </div>
      <button class="btn-secondary" :disabled="genInv" @click="downloadInventory">
        <Icon name="download" :size="16" />{{ genInv ? t('export.generating') : t('export.inventory_btn') }}
      </button>
    </section>

    <!-- Certificate -->
    <section class="panel animate-rise">
      <div class="px-5 py-4 border-b border-line flex items-start gap-4">
        <span class="w-11 h-11 rounded-xl bg-moss-400/10 border border-moss-400/25 text-moss-400 grid place-items-center flex-shrink-0">
          <Icon name="certificate" :size="20" />
        </span>
        <div>
          <h2 class="font-display font-semibold text-fg text-[17px]">{{ t('export.hkn_title') }}</h2>
          <p class="text-sm text-fg-muted mt-0.5">{{ t('export.hkn_desc') }}</p>
        </div>
      </div>

      <div v-if="exportError" class="alert-error m-5 mb-0"><Icon name="alert" :size="16" />{{ exportError }}</div>

      <div class="grid lg:grid-cols-2">
        <!-- Step 1 -->
        <div class="p-5 lg:border-r border-line">
          <div class="flex items-center justify-between mb-3">
            <h3 class="step"><span>1</span>{{ t('export.select_animals') }}</h3>
            <span class="badge-gray num">{{ selectedIds.length }}</span>
          </div>
          <div class="relative mb-3">
            <Icon name="search" :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-fg-faint pointer-events-none" />
            <input v-model="searchTerm" @input="applySearch" :placeholder="t('common.search')" class="!pl-9" />
          </div>
          <div class="max-h-[380px] overflow-y-auto rounded-xl border border-line divide-y divide-line/70 bg-ink-950/40">
            <div v-if="loading" class="p-6 text-fg-faint text-sm text-center">{{ t('common.loading') }}</div>
            <label v-for="a in (searchTerm ? filteredAnimals : allAnimals)" :key="a.id"
                   class="flex items-center gap-3 px-3 py-2.5 mb-0 cursor-pointer transition-colors font-normal"
                   :class="selectedIds.includes(a.id) ? 'bg-moss-400/[0.07]' : 'hover:bg-ink-850'">
              <input type="checkbox" :checked="selectedIds.includes(a.id)" @change="toggleAnimal(a.id)" />
              <AnimalAvatar :animal="a" size="w-9 h-9" rounded="rounded-lg" />
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-semibold text-fg truncate">{{ a.name }}</span>
                  <span :class="sexBadge(a.sex)">{{ sexNotation(a.sex) }}</span>
                </div>
                <p class="text-xs text-fg-faint italic truncate">{{ a.species }}</p>
              </div>
              <span v-if="a.tracking_id" class="text-xs text-fg-faint num flex-shrink-0">#{{ a.tracking_id }}</span>
            </label>
            <div v-if="!loading && allAnimals.length === 0" class="p-6 text-fg-faint text-sm text-center">{{ t('animal.noAnimals') }}</div>
          </div>
        </div>

        <!-- Steps 2-4 -->
        <div class="p-5 space-y-6 border-t lg:border-t-0 border-line">
          <label class="option" :class="{ on: blanko }">
            <input type="checkbox" v-model="blanko" />
            <span><span class="option-title block">{{ t('export.blanko_label') }}</span><span class="option-desc block">{{ t('export.blanko_hint') }}</span></span>
          </label>

          <div v-if="!blanko">
            <h3 class="step mb-3"><span>2</span>{{ t('export.buyer') }}</h3>
            <div class="grid sm:grid-cols-2 gap-2.5">
              <input v-model="buyer.name"     :placeholder="t('export.buyer_name')" class="sm:col-span-2" />
              <input v-model="buyer.street"   :placeholder="t('export.buyer_street')" class="sm:col-span-2" />
              <input v-model="buyer.zip_city" :placeholder="t('export.buyer_zip')" />
              <input v-model="buyer.phone"    :placeholder="t('export.buyer_phone')" />
            </div>
          </div>

          <div>
            <h3 class="step mb-3"><span>{{ blanko ? 2 : 3 }}</span>{{ t('export.origin') }}</h3>
            <div class="grid sm:grid-cols-2 gap-2">
              <label v-for="val in ['bestand','nachzucht','einfuhr','sonstiges']" :key="val"
                     class="option !items-center" :class="{ on: originType === val }">
                <input type="radio" :value="val" v-model="originType" />
                <span class="option-title !font-medium">{{ t('export.origins.' + val) }}</span>
              </label>
            </div>
            <div v-if="originType === 'einfuhr'" class="grid grid-cols-2 gap-2.5 mt-2.5">
              <input v-model="citesNr" :placeholder="t('export.cites_nr')" />
              <input v-model="einfuhrNr" :placeholder="t('export.einfuhr_nr')" />
            </div>
            <input v-if="originType === 'sonstiges'" v-model="sonstigesText" :placeholder="t('export.sonstiges_placeholder')" class="mt-2.5" />
          </div>

          <div v-if="!blanko">
            <h3 class="step mb-3"><span>4</span>{{ t('export.location') }}</h3>
            <input v-model="ort" :placeholder="t('export.location_placeholder')" />
            <p class="hint">{{ t('export.location_hint') }}</p>
          </div>
        </div>
      </div>

      <div class="px-5 py-4 border-t border-line bg-ink-950/40 flex flex-wrap gap-3 items-center justify-between">
        <span class="text-xs text-fg-faint flex items-center gap-1.5"><Icon name="shield" :size="14" />{{ t('export.legal_hint') }}</span>
        <button class="btn-primary" :disabled="genHkn || !selectedIds.length" @click="downloadHkn">
          <Icon name="download" :size="16" />{{ genHkn ? t('export.generating') : (blanko ? t('export.blanko_btn') : t('export.generate_btn')) }}
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.step { @apply flex items-center gap-2.5 font-display font-semibold text-[15px] text-fg; }
.step > span { @apply w-6 h-6 rounded-md bg-ink-800 border border-line-strong grid place-items-center font-mono text-[11px] text-moss-400; }
</style>
