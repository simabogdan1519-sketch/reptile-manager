<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from '@/i18n'
import { useAuthStore } from '@/stores/auth'
import { users as usersApi, groups as groupsApi } from '@/api'
import { errorMessage } from '@/utils/format'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'

const { t } = useI18n()
const auth = useAuthStore()

const tab = ref('users')
const userList = ref([])
const groupList = ref([])
const loading = ref(true)
const error = ref('')

const groupName = computed(() => Object.fromEntries(groupList.value.map(g => [g.id, g.name])))
const userName  = computed(() => Object.fromEntries(userList.value.map(u => [u.id, u.username])))

const errMsg = errorMessage

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [u, g] = await Promise.all([usersApi.list(), groupsApi.list()])
    userList.value = u.data
    groupList.value = g.data
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ── User editor ───────────────────────────────────────────────────────────────
const userForm = ref(null)   // null = closed
const userSaving = ref(false)
const userError = ref('')

function newUser() {
  userError.value = ''
  userForm.value = { id: null, username: '', password: '', email: '', is_admin: false, is_active: true, group_ids: [] }
}
function editUser(u) {
  userError.value = ''
  userForm.value = { id: u.id, username: u.username, password: '', email: u.email || '',
    is_admin: u.is_admin, is_active: u.is_active, group_ids: u.groups.map(g => g.id) }
}
async function saveUser() {
  userSaving.value = true
  userError.value = ''
  try {
    const f = { ...userForm.value }
    const payload = { username: f.username, email: f.email || null, is_admin: f.is_admin,
      is_active: f.is_active, group_ids: f.group_ids }
    if (f.password) payload.password = f.password
    if (f.id) await usersApi.update(f.id, payload)
    else      await usersApi.create({ ...payload, password: f.password })
    userForm.value = null
    await load()
    if (f.id === auth.user?.id) await auth.fetchMe()
  } catch (e) {
    userError.value = errMsg(e)
  } finally {
    userSaving.value = false
  }
}
async function deleteUser(u) {
  if (!confirm(`${t('access.confirm_delete_user')}\n${u.username}`)) return
  try { await usersApi.delete(u.id); await load() } catch (e) { alert(errMsg(e)) }
}

// ── Group editor ──────────────────────────────────────────────────────────────
const groupForm = ref(null)
const groupSaving = ref(false)
const groupError = ref('')

function newGroup() {
  groupError.value = ''
  groupForm.value = { id: null, name: '', description: '', member_ids: [] }
}
function editGroup(g) {
  groupError.value = ''
  groupForm.value = { id: g.id, name: g.name, description: g.description || '', member_ids: [...g.member_ids] }
}
async function saveGroup() {
  groupSaving.value = true
  groupError.value = ''
  try {
    const f = groupForm.value
    const payload = { name: f.name, description: f.description || null, member_ids: f.member_ids }
    if (f.id) await groupsApi.update(f.id, payload)
    else      await groupsApi.create(payload)
    groupForm.value = null
    await load()
    await auth.fetchMe()
  } catch (e) {
    groupError.value = errMsg(e)
  } finally {
    groupSaving.value = false
  }
}
async function deleteGroup(g) {
  if (!confirm(`${t('access.confirm_delete_group')}\n${g.name}`)) return
  try { await groupsApi.delete(g.id); await load() } catch (e) { alert(errMsg(e)) }
}

function toggle(arr, id) {
  const i = arr.indexOf(id)
  if (i === -1) arr.push(id); else arr.splice(i, 1)
}
</script>

<template>
  <div>
    <PageHeader :eyebrow="t('access.eyebrow')" :title="t('access.nav')" :subtitle="t('access.subtitle')">
      <template #actions>
        <div class="seg h-9 items-center">
          <button v-for="k in ['users','groups']" :key="k" :class="{ on: tab === k }" @click="tab = k">
            {{ t(`access.${k}`) }} <span class="num text-fg-faint ml-1">{{ k === 'users' ? userList.length : groupList.length }}</span>
          </button>
        </div>
        <button class="btn-primary" @click="tab === 'users' ? newUser() : newGroup()">
          <Icon name="plus" :size="16" />{{ tab === 'users' ? t('access.add_user') : t('access.add_group') }}
        </button>
      </template>
    </PageHeader>

    <div v-if="error" class="alert-error mb-4"><Icon name="alert" :size="16" />{{ error }}</div>
    <div v-if="loading" class="card h-48 animate-pulse" />

    <!-- USERS -->
    <section v-else-if="tab === 'users'" class="panel animate-rise">
      <EmptyState v-if="!userList.length" icon="users" :title="t('access.no_users')" />
      <ul v-else class="divide-y divide-line/70">
        <li v-for="u in userList" :key="u.id" class="flex flex-col sm:flex-row sm:items-center gap-3 px-5 py-4 hover:bg-ink-850/60 transition-colors">
          <div class="flex items-center gap-3.5 flex-1 min-w-0">
            <div class="w-10 h-10 rounded-xl grid place-items-center font-display font-bold flex-shrink-0"
                 :class="u.is_admin ? 'bg-heat-400/15 text-heat-400 border border-heat-400/30' : 'bg-ink-800 text-fg border border-line-strong'">
              {{ u.username[0]?.toUpperCase() }}
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-semibold text-fg">{{ u.username }}</span>
                <span v-if="u.id === auth.user?.id" class="text-xs text-fg-faint">({{ t('access.you') }})</span>
                <span v-if="u.is_admin" class="badge-yellow"><Icon name="shield" :size="11" />{{ t('access.admin') }}</span>
                <span v-if="!u.is_active" class="badge-red">{{ t('access.disabled') }}</span>
              </div>
              <div class="flex flex-wrap gap-1.5 mt-1.5">
                <span v-for="g in u.groups" :key="g.id" class="badge-gray"><Icon name="group" :size="11" />{{ g.name }}</span>
                <span v-if="!u.groups.length && !u.is_admin" class="text-xs text-fg-faint">{{ t('access.no_membership') }}</span>
                <span v-if="u.is_admin && !u.groups.length" class="text-xs text-fg-faint">{{ t('access.sees_all') }}</span>
              </div>
            </div>
          </div>
          <div class="flex gap-1.5 flex-shrink-0">
            <button class="btn-secondary btn-sm" @click="editUser(u)"><Icon name="edit" :size="14" />{{ t('common.edit') }}</button>
            <button class="btn-danger btn-sm btn-icon" :disabled="u.id === auth.user?.id" @click="deleteUser(u)"><Icon name="trash" :size="14" /></button>
          </div>
        </li>
      </ul>
    </section>

    <!-- GROUPS -->
    <template v-else>
      <div v-if="!groupList.length" class="card"><EmptyState icon="group" :title="t('access.groups')" :text="t('access.no_groups')" /></div>
      <div v-else class="grid sm:grid-cols-2 xl:grid-cols-3 gap-4 stagger">
        <article v-for="g in groupList" :key="g.id" class="card flex flex-col">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <h3 class="font-display font-semibold text-[18px] text-fg truncate">{{ g.name }}</h3>
              <p class="text-xs text-fg-faint mt-0.5 min-h-[16px]">{{ g.description }}</p>
            </div>
            <span class="badge-green num flex-shrink-0"><Icon name="reptile" :size="12" />{{ g.animal_count }}</span>
          </div>
          <p class="eyebrow mt-4 mb-2">{{ t('access.members') }}</p>
          <div class="flex flex-wrap gap-1.5 flex-1 content-start">
            <span v-for="id in g.member_ids" :key="id" class="badge-gray"><Icon name="user" :size="11" />{{ userName[id] ?? '#' + id }}</span>
            <span v-if="!g.member_ids.length" class="text-xs text-fg-faint">—</span>
          </div>
          <div class="flex gap-1.5 mt-5 pt-4 border-t border-line">
            <button class="btn-secondary btn-sm flex-1" @click="editGroup(g)"><Icon name="edit" :size="14" />{{ t('common.edit') }}</button>
            <button class="btn-danger btn-sm btn-icon" @click="deleteGroup(g)"><Icon name="trash" :size="14" /></button>
          </div>
        </article>
      </div>
    </template>

    <!-- User modal -->
    <Modal :open="!!userForm" :title="userForm?.id ? t('access.edit_user') : t('access.add_user')" icon="user" width="max-w-lg" @close="userForm = null">
      <form v-if="userForm" id="userForm" class="space-y-4" @submit.prevent="saveUser">
        <div v-if="userError" class="alert-error"><Icon name="alert" :size="16" />{{ userError }}</div>
        <div class="grid sm:grid-cols-2 gap-4">
          <div><label>{{ t('access.username') }} *</label><input v-model="userForm.username" required autocomplete="off" /></div>
          <div><label>{{ t('access.email') }}</label><input v-model="userForm.email" type="email" autocomplete="off" /></div>
          <div class="sm:col-span-2">
            <label>{{ t('access.password') }} {{ userForm.id ? '' : '*' }}</label>
            <input v-model="userForm.password" type="password" :required="!userForm.id" minlength="6" autocomplete="new-password" />
            <p v-if="userForm.id" class="hint">{{ t('access.password_keep') }}</p>
          </div>
        </div>
        <div class="grid sm:grid-cols-2 gap-2">
          <label class="option" :class="{ on: userForm.is_admin }">
            <input type="checkbox" v-model="userForm.is_admin" />
            <span><span class="option-title block">{{ t('access.admin') }}</span><span class="option-desc block">{{ t('access.admin_hint') }}</span></span>
          </label>
          <label class="option" :class="{ on: userForm.is_active }">
            <input type="checkbox" v-model="userForm.is_active" />
            <span><span class="option-title block">{{ t('access.active') }}</span><span class="option-desc block">{{ t('access.active_hint') }}</span></span>
          </label>
        </div>
        <div>
          <label>{{ t('access.member_of') }}</label>
          <p v-if="!groupList.length" class="text-sm text-fg-faint">{{ t('access.no_groups') }}</p>
          <div class="flex flex-wrap gap-2">
            <button v-for="g in groupList" :key="g.id" type="button" class="chip" :class="{ on: userForm.group_ids.includes(g.id) }"
                    @click="toggle(userForm.group_ids, g.id)">
              <Icon :name="userForm.group_ids.includes(g.id) ? 'check' : 'plus'" :size="13" />{{ g.name }}
            </button>
          </div>
        </div>
      </form>
      <template #footer>
        <button class="btn-ghost" @click="userForm = null">{{ t('common.cancel') }}</button>
        <button class="btn-primary" form="userForm" :disabled="userSaving">{{ userSaving ? t('common.saving') : t('common.save') }}</button>
      </template>
    </Modal>

    <!-- Group modal -->
    <Modal :open="!!groupForm" :title="groupForm?.id ? t('access.edit_group') : t('access.add_group')" icon="group" width="max-w-lg" @close="groupForm = null">
      <form v-if="groupForm" id="groupForm" class="space-y-4" @submit.prevent="saveGroup">
        <div v-if="groupError" class="alert-error"><Icon name="alert" :size="16" />{{ groupError }}</div>
        <div><label>{{ t('access.group_name') }} *</label><input v-model="groupForm.name" required /></div>
        <div><label>{{ t('access.description') }}</label><input v-model="groupForm.description" /></div>
        <div>
          <label>{{ t('access.members') }}</label>
          <div class="flex flex-wrap gap-2">
            <button v-for="u in userList.filter(x => !x.is_admin)" :key="u.id" type="button" class="chip" :class="{ on: groupForm.member_ids.includes(u.id) }"
                    @click="toggle(groupForm.member_ids, u.id)">
              <Icon :name="groupForm.member_ids.includes(u.id) ? 'check' : 'plus'" :size="13" />{{ u.username }}
            </button>
            <span v-if="!userList.filter(x => !x.is_admin).length" class="text-sm text-fg-faint">{{ t('access.no_regular_users') }}</span>
          </div>
          <p class="hint">{{ t('access.admin_hint') }}</p>
        </div>
      </form>
      <template #footer>
        <button class="btn-ghost" @click="groupForm = null">{{ t('common.cancel') }}</button>
        <button class="btn-primary" form="groupForm" :disabled="groupSaving">{{ groupSaving ? t('common.saving') : t('common.save') }}</button>
      </template>
    </Modal>
  </div>
</template>
