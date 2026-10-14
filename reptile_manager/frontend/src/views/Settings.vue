<script setup>
import { ref, computed, onMounted } from 'vue'
import { ha, auth as authApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useI18n, setLocale, languages } from '@/i18n'
import { errorMessage } from '@/utils/format'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import Brand from '@/components/Brand.vue'

const auth = useAuthStore()
const { t, locale } = useI18n()

const config = ref(null)
const haToken = ref('')
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const syncing = ref(false)
const testResult = ref(null)
const notice = ref(null)   // { ok: bool, text }
const currentApiUrl = computed(() => window.__REPTILE_API__ || import.meta.env.VITE_API_URL || t('settings.api_auto'))

const pw = ref({ current: '', next: '' })
const pwMsg = ref('')
const pwErr = ref('')
const pwSaving = ref(false)

const section = ref('account')
const sections = computed(() => [
  { id: 'account', icon: 'user', label: t('settings.sec_account') },
  ...(auth.isAdmin ? [
    { id: 'breeder', icon: 'certificate', label: t('settings.sec_breeder') },
    { id: 'ha', icon: 'home', label: t('settings.sec_ha') },
    { id: 'integration', icon: 'code', label: t('settings.sec_integration') },
  ] : []),
  { id: 'about', icon: 'info', label: t('settings.sec_about') },
])

onMounted(async () => {
  try { config.value = (await ha.getConfig()).data }
  finally { loading.value = false }
})

function flash(ok, text) {
  notice.value = { ok, text }
  setTimeout(() => (notice.value = null), 3500)
}

async function changePassword() {
  pwMsg.value = ''; pwErr.value = ''; pwSaving.value = true
  try {
    await authApi.changePassword(pw.value.current, pw.value.next)
    pw.value = { current: '', next: '' }
    pwMsg.value = t('access.password_changed')
  } catch (e) {
    pwErr.value = errorMessage(e)
  } finally {
    pwSaving.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    const payload = { ...config.value }
    if (haToken.value) payload.ha_token = haToken.value
    config.value = (await ha.updateConfig(payload)).data
    haToken.value = ''
    flash(true, t('settings.saved'))
  } catch (e) {
    flash(false, errorMessage(e))
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try { testResult.value = (await ha.test()).data }
  catch (e) { testResult.value = { success: false, error: errorMessage(e) } }
  finally { testing.value = false }
}

async function syncNow() {
  syncing.value = true
  try { await ha.sync(); flash(true, t('settings.sync_ok')) }
  catch (e) { flash(false, t('settings.sync_failed') + ': ' + errorMessage(e)) }
  finally { syncing.value = false }
}

const yaml = computed(() => `# ${t('settings.yaml_step1')}
sensor:
  - platform: rest
    resource: http://YOUR_HA_IP:8000/api/ha/sensors
    scan_interval: 300
    name: reptile_manager_data
    json_attributes:
      - summary
      - animals

# ${t('settings.yaml_step2')}
template:
  - sensor:
      - name: "Reptiles active"
        state: "{{ state_attr('sensor.reptile_manager_data', 'summary')['active_animals'] | default(0) }}"
        unit_of_measurement: "animals"
        icon: mdi:snake

      - name: "Reptiles not fed"
        state: "{{ state_attr('sensor.reptile_manager_data', 'summary')['animals_not_fed'] | default(0) }}"
        unit_of_measurement: "animals"
        icon: mdi:food-off

# ${t('settings.yaml_step3')}
automation:
  - alias: "Reptile feeding reminder"
    trigger:
      - platform: numeric_state
        entity_id: sensor.reptiles_not_fed
        above: 0
    action:
      - service: notify.mobile_app_your_phone
        data:
          message: >
            {{ states('sensor.reptiles_not_fed') }} reptile(s) need food!`)

const copied = ref(false)
async function copyYaml() {
  try { await navigator.clipboard.writeText(yaml.value); copied.value = true; setTimeout(() => (copied.value = false), 1500) } catch { /* ignore */ }
}

const events = computed(() => [
  { type: 'reptile_feeding',  desc: t('settings.ev_feeding'),  fields: 'animal_name, food_type, food_size, accepted' },
  { type: 'reptile_shedding', desc: t('settings.ev_shedding'), fields: 'animal_name, complete, in_one_piece' },
  { type: 'reptile_breeding', desc: t('settings.ev_breeding'), fields: 'female_name, male_name, date_paired' },
])
</script>

<template>
  <div>
    <PageHeader :eyebrow="t('settings.eyebrow')" :title="t('settings.title')" />

    <Transition name="fade">
      <div v-if="notice" class="fixed bottom-5 right-5 z-50" :class="notice.ok ? 'alert-ok' : 'alert-error'" style="backdrop-filter: blur(8px)">
        <Icon :name="notice.ok ? 'check' : 'alert'" :size="16" />{{ notice.text }}
      </div>
    </Transition>

    <div class="grid lg:grid-cols-[220px_1fr] gap-6 items-start">
      <!-- Section nav -->
      <nav class="lg:sticky lg:top-10 flex lg:flex-col gap-1 overflow-x-auto scrollbar-none -mx-1 px-1">
        <button v-for="s in sections" :key="s.id" class="snav" :class="{ on: section === s.id }" @click="section = s.id">
          <Icon :name="s.icon" :size="16" />{{ s.label }}
        </button>
      </nav>

      <div v-if="loading" class="card h-64 animate-pulse" />

      <div v-else class="space-y-4 min-w-0 animate-rise" :key="section">
        <!-- Account -->
        <template v-if="section === 'account'">
          <section class="card">
            <h2 class="panel-title mb-1">{{ t('settings.language') }}</h2>
            <p class="text-sm text-fg-muted mb-4">{{ t('settings.languageNote') }}</p>
            <div class="grid sm:grid-cols-2 gap-2 max-w-md">
              <label v-for="(lang, code) in languages" :key="code" class="option !items-center" :class="{ on: locale === code }">
                <input type="radio" :checked="locale === code" @change="setLocale(code)" />
                <span class="option-title">{{ lang.name }}</span>
                <span class="ml-auto eyebrow">{{ lang.short }}</span>
              </label>
            </div>
          </section>

          <section class="card">
            <h2 class="panel-title mb-1">{{ t('access.change_password') }}</h2>
            <p class="text-sm text-fg-muted mb-4">{{ t('settings.password_hint', { user: auth.user?.username }) }}</p>
            <form class="grid sm:grid-cols-2 gap-4 max-w-xl" @submit.prevent="changePassword">
              <div><label>{{ t('access.current_password') }}</label><input type="password" v-model="pw.current" required autocomplete="current-password" /></div>
              <div><label>{{ t('access.new_password') }}</label><input type="password" v-model="pw.next" required minlength="6" autocomplete="new-password" /></div>
              <div class="sm:col-span-2 flex flex-wrap items-center gap-3">
                <button class="btn-primary" :disabled="pwSaving"><Icon name="key" :size="15" />{{ pwSaving ? t('common.saving') : t('access.change_password') }}</button>
                <span v-if="pwMsg" class="text-sm text-moss-400 flex items-center gap-1"><Icon name="check" :size="15" />{{ pwMsg }}</span>
                <span v-if="pwErr" class="text-sm text-coral-400 flex items-center gap-1"><Icon name="alert" :size="15" />{{ pwErr }}</span>
              </div>
            </form>
          </section>
        </template>

        <!-- Breeder profile -->
        <section v-else-if="section === 'breeder' && config" class="card">
          <h2 class="panel-title mb-1">{{ t('settings.breeder_title') }}</h2>
          <p class="text-sm text-fg-muted mb-5">{{ t('settings.breeder_desc') }}</p>
          <form class="grid sm:grid-cols-2 gap-4" @submit.prevent="saveConfig">
            <div><label>{{ t('settings.breeder_name') }}</label><input v-model="config.breeder_name" /></div>
            <div><label>{{ t('export.buyer_phone') }}</label><input v-model="config.breeder_phone" /></div>
            <div><label>{{ t('export.buyer_street') }}</label><input v-model="config.breeder_street" /></div>
            <div><label>{{ t('export.buyer_zip') }}</label><input v-model="config.breeder_zip_city" /></div>
            <div class="sm:col-span-2"><button class="btn-primary" :disabled="saving">{{ saving ? t('common.saving') : t('common.save') }}</button></div>
          </form>
        </section>

        <!-- Home Assistant -->
        <template v-else-if="section === 'ha' && config">
          <section class="card">
            <div class="flex items-start gap-4 mb-5">
              <span class="w-11 h-11 rounded-xl bg-lagoon-400/10 border border-lagoon-400/25 text-lagoon-400 grid place-items-center flex-shrink-0"><Icon name="home" :size="20" /></span>
              <div class="flex-1">
                <h2 class="panel-title">{{ t('settings.ha') }}</h2>
                <p class="text-sm text-fg-muted">{{ t('settings.ha_desc') }}</p>
              </div>
              <label class="option !p-2 !px-3 !items-center" :class="{ on: config.enabled }">
                <input type="checkbox" v-model="config.enabled" /><span class="option-title">{{ t('common.enabled') }}</span>
              </label>
            </div>

            <form class="space-y-4" @submit.prevent="saveConfig">
              <div class="grid sm:grid-cols-2 gap-4">
                <div><label>{{ t('settings.ha_url') }}</label><input v-model="config.ha_url" type="url" placeholder="http://homeassistant.local:8123" /><p class="hint">{{ t('settings.ha_url_hint') }}</p></div>
                <div><label>{{ t('settings.ha_token') }}</label><input v-model="haToken" type="password" :placeholder="t('settings.token_keep')" /><p class="hint">{{ t('settings.token_hint') }}</p></div>
                <div><label>{{ t('settings.webhook_id') }}</label><input v-model="config.webhook_id" placeholder="reptile_manager_events" class="num" /><p class="hint">{{ t('settings.webhook_hint') }}</p></div>
                <div><label>{{ t('settings.reminder_days') }}</label><input type="number" v-model="config.feeding_reminder_days" min="1" max="90" class="num" /></div>
              </div>

              <div>
                <p class="section-title mb-3">{{ t('settings.notify') }}</p>
                <div class="grid sm:grid-cols-3 gap-2">
                  <label class="option" :class="{ on: config.notify_feeding }"><input type="checkbox" v-model="config.notify_feeding" /><span class="option-title">{{ t('settings.notify_feeding') }}</span></label>
                  <label class="option" :class="{ on: config.notify_shedding }"><input type="checkbox" v-model="config.notify_shedding" /><span class="option-title">{{ t('settings.notify_shedding') }}</span></label>
                  <label class="option" :class="{ on: config.notify_breeding }"><input type="checkbox" v-model="config.notify_breeding" /><span class="option-title">{{ t('settings.notify_breeding') }}</span></label>
                </div>
              </div>

              <div class="flex flex-wrap gap-2 pt-2">
                <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? t('common.saving') : t('common.save') }}</button>
                <button type="button" class="btn-secondary" :disabled="testing" @click="testConnection"><Icon name="plug" :size="15" />{{ testing ? t('settings.testing') : t('settings.test') }}</button>
                <button type="button" class="btn-secondary" :disabled="syncing || !config.enabled" @click="syncNow"><Icon name="sync" :size="15" />{{ syncing ? t('settings.syncing') : t('settings.sync') }}</button>
              </div>
              <div v-if="testResult" :class="testResult.success ? 'alert-ok' : 'alert-error'">
                <Icon :name="testResult.success ? 'check' : 'alert'" :size="16" />{{ testResult.success ? testResult.message : testResult.error }}
              </div>
            </form>
          </section>

          <section class="card">
            <h2 class="panel-title mb-1">{{ t('settings.api_url') }}</h2>
            <p class="text-sm text-fg-muted mb-3">{{ t('settings.api_url_hint') }}</p>
            <div class="rounded-lg border border-line bg-ink-950 px-3 py-2.5 font-mono text-xs text-fg-muted break-all">{{ currentApiUrl }}</div>
          </section>
        </template>

        <!-- Integration snippets -->
        <template v-else-if="section === 'integration'">
          <section class="panel">
            <div class="panel-head">
              <div>
                <h2 class="panel-title">{{ t('settings.yaml_title') }}</h2>
                <p class="text-xs text-fg-muted mt-0.5">{{ t('settings.yaml_desc') }}</p>
              </div>
              <button class="btn-secondary btn-sm" @click="copyYaml"><Icon :name="copied ? 'check' : 'file'" :size="14" />{{ copied ? t('common.copied') : t('common.copy') }}</button>
            </div>
            <pre class="p-5 text-[12px] leading-relaxed text-fg-muted overflow-x-auto font-mono bg-ink-950/60">{{ yaml }}</pre>
          </section>

          <section class="card">
            <h2 class="panel-title mb-1">{{ t('settings.webhooks') }}</h2>
            <p class="text-sm text-fg-muted mb-4">{{ t('settings.webhooks_desc') }}</p>
            <div class="space-y-2">
              <div v-for="ev in events" :key="ev.type" class="tile flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4">
                <code class="text-[12.5px]">{{ ev.type }}</code>
                <span class="text-sm text-fg-muted flex-1">{{ ev.desc }}</span>
                <span class="text-xs text-fg-faint font-mono">{{ ev.fields }}</span>
              </div>
            </div>
          </section>
        </template>

        <!-- About -->
        <section v-else-if="section === 'about'" class="card">
          <div class="flex items-center gap-4 mb-5">
            <Brand :size="52" />
            <div>
              <div class="font-display text-xl font-semibold text-fg">Reptile Manager</div>
              <div class="text-sm text-fg-muted num">v1.3.0 · {{ t('settings.about_edition') }}</div>
            </div>
          </div>
          <p class="text-sm text-fg-muted leading-relaxed mb-5 max-w-2xl">{{ t('settings.about_text') }}</p>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-5">
            <div class="tile"><div class="eyebrow mb-1">{{ t('settings.author') }}</div><div class="text-fg text-sm font-semibold">demrios-de</div></div>
            <div class="tile"><div class="eyebrow mb-1">{{ t('settings.licence') }}</div><div class="text-fg text-sm font-semibold">MIT</div></div>
            <div class="tile"><div class="eyebrow mb-1">Backend</div><div class="text-fg text-sm font-semibold">FastAPI · SQLite</div></div>
            <div class="tile"><div class="eyebrow mb-1">Frontend</div><div class="text-fg text-sm font-semibold">Vue 3 · Tailwind</div></div>
          </div>
          <div class="flex flex-wrap gap-2">
            <a href="https://github.com/demrios-de/reptile-manager" target="_blank" rel="noopener" class="btn-secondary btn-sm"><Icon name="github" :size="15" />GitHub</a>
            <a href="https://github.com/demrios-de/reptile-manager/issues" target="_blank" rel="noopener" class="btn-ghost btn-sm"><Icon name="external" :size="14" />{{ t('settings.report_bug') }}</a>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.snav { @apply flex items-center gap-2.5 h-9 px-3 rounded-lg text-[13.5px] font-medium text-fg-muted whitespace-nowrap transition-colors hover:text-fg hover:bg-ink-800/70; }
.snav.on { @apply text-fg bg-ink-800; box-shadow: inset 0 0 0 1px rgb(var(--line-strong)); }
.snav.on :deep(svg) { @apply text-moss-400; }
.fade-enter-active, .fade-leave-active { transition: opacity .2s, transform .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(6px); }
</style>
