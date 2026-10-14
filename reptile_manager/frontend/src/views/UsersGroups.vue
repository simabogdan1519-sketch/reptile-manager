<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from '@/i18n'
import { useAuthStore } from '@/stores/auth'
import { users as usersApi, groups as groupsApi } from '@/api'

const { t } = useI18n()
const auth = useAuthStore()

const tab = ref('users')
const userList = ref([])
const groupList = ref([])
const loading = ref(true)
const error = ref('')

const groupName = computed(() => Object.fromEntries(groupList.value.map(g => [g.id, g.name])))
const userName  = computed(() => Object.fromEntries(userList.value.map(u => [u.id, u.username])))

function errMsg(e) {
  const d = e.response?.data?.detail
  return Array.isArray(d) ? d.map(x => x.msg).join(', ') : (d || e.message)
}

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
  <div class="max-w-4xl">
    <h1 class="text-2xl font-bold text-slate-200 mb-6">👥 {{ t('access.nav') }}</h1>

    <div class="flex gap-2 mb-6">
      <button v-for="k in ['users','groups']" :key="k" type="button"
        class="px-4 py-1.5 rounded-lg text-sm font-medium border transition-all"
        :class="tab === k ? 'bg-brand-600 border-brand-500 text-white'
                          : 'bg-surface-600 border-surface-500 text-slate-400 hover:text-slate-200'"
        @click="tab = k">
        {{ t(`access.${k}`) }}
        <span class="ml-1 opacity-60">{{ k === 'users' ? userList.length : groupList.length }}</span>
      </button>
    </div>

    <div v-if="error" class="bg-red-900/40 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm mb-4">⚠ {{ error }}</div>
    <div v-if="loading" class="text-slate-500 text-center py-16">{{ t('common.loading') }}</div>

    <!-- ── USERS ─────────────────────────────────────────────────────────── -->
    <template v-else-if="tab === 'users'">
      <div class="flex justify-end mb-4">
        <button class="btn-primary btn-sm" @click="newUser">+ {{ t('access.add_user') }}</button>
      </div>

      <form v-if="userForm" class="card space-y-4 mb-6" @submit.prevent="saveUser">
        <h2 class="font-semibold text-slate-200">{{ userForm.id ? t('access.edit_user') : t('access.add_user') }}</h2>
        <div v-if="userError" class="bg-red-900/40 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm">⚠ {{ userError }}</div>
        <div class="grid sm:grid-cols-2 gap-4">
          <div><label>{{ t('access.username') }} *</label><input v-model="userForm.username" required autocomplete="off" /></div>
          <div><label>{{ t('access.email') }}</label><input v-model="userForm.email" type="email" autocomplete="off" /></div>
          <div class="sm:col-span-2">
            <label>{{ t('access.password') }} {{ userForm.id ? '' : '*' }}</label>
            <input v-model="userForm.password" type="password" :required="!userForm.id" minlength="6" autocomplete="new-password" />
            <p v-if="userForm.id" class="text-xs text-slate-600 mt-1">{{ t('access.password_keep') }}</p>
          </div>
        </div>
        <div class="flex flex-wrap gap-6">
          <label class="flex items-center gap-2 cursor-pointer mb-0">
            <input type="checkbox" v-model="userForm.is_admin" class="w-4 h-4" /> {{ t('access.admin') }}
          </label>
          <label class="flex items-center gap-2 cursor-pointer mb-0">
            <input type="checkbox" v-model="userForm.is_active" class="w-4 h-4" /> {{ t('access.active') }}
          </label>
        </div>
        <p v-if="userForm.is_admin" class="text-xs text-slate-500">{{ t('access.admin_hint') }}</p>
        <div>
          <label>{{ t('access.member_of') }}</label>
          <p v-if="!groupList.length" class="text-sm text-slate-500">{{ t('access.no_groups') }}</p>
          <div class="flex flex-wrap gap-2">
            <button v-for="g in groupList" :key="g.id" type="button"
              class="px-3 py-1 rounded-full text-sm border transition-all"
              :class="userForm.group_ids.includes(g.id) ? 'bg-brand-600 border-brand-500 text-white'
                      : 'bg-surface-600 border-surface-500 text-slate-400 hover:text-slate-200'"
              @click="toggle(userForm.group_ids, g.id)">
              {{ userForm.group_ids.includes(g.id) ? '✓ ' : '' }}{{ g.name }}
            </button>
          </div>
        </div>
        <div class="flex gap-3">
          <button class="btn-primary btn-sm" :disabled="userSaving">{{ userSaving ? t('common.saving') : t('common.save') }}</button>
          <button type="button" class="btn-secondary btn-sm" @click="userForm = null">{{ t('common.cancel') }}</button>
        </div>
      </form>

      <div v-if="!userList.length" class="text-slate-500 text-center py-10">{{ t('access.no_users') }}</div>
      <div v-else class="card p-0 overflow-hidden">
        <div v-for="u in userList" :key="u.id"
             class="border-b border-surface-600 hover:bg-surface-600/50 transition-colors flex flex-col sm:flex-row sm:items-center gap-2 px-4 py-3 last:border-b-0">
          <div class="flex items-center gap-3 flex-1 min-w-0">
            <div class="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
              {{ u.username[0]?.toUpperCase() }}
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-medium text-slate-200">{{ u.username }}</span>
                <span v-if="u.id === auth.user?.id" class="text-xs text-slate-500">({{ t('access.you') }})</span>
                <span v-if="u.is_admin" class="badge-yellow">{{ t('access.admin') }}</span>
                <span v-if="!u.is_active" class="badge-red">{{ t('access.disabled') }}</span>
              </div>
              <div class="flex flex-wrap gap-1 mt-1">
                <span v-for="g in u.groups" :key="g.id" class="badge-blue">{{ g.name }}</span>
              </div>
            </div>
          </div>
          <div class="flex gap-2 flex-shrink-0">
            <button class="btn-secondary btn-sm" @click="editUser(u)">{{ t('common.edit') }}</button>
            <button class="btn-danger btn-sm" :disabled="u.id === auth.user?.id" @click="deleteUser(u)">🗑</button>
          </div>
        </div>
      </div>
    </template>

    <!-- ── GROUPS ────────────────────────────────────────────────────────── -->
    <template v-else>
      <div class="flex justify-end mb-4">
        <button class="btn-primary btn-sm" @click="newGroup">+ {{ t('access.add_group') }}</button>
      </div>

      <form v-if="groupForm" class="card space-y-4 mb-6" @submit.prevent="saveGroup">
        <h2 class="font-semibold text-slate-200">{{ groupForm.id ? t('access.edit_group') : t('access.add_group') }}</h2>
        <div v-if="groupError" class="bg-red-900/40 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm">⚠ {{ groupError }}</div>
        <div class="grid sm:grid-cols-2 gap-4">
          <div><label>{{ t('access.group_name') }} *</label><input v-model="groupForm.name" required /></div>
          <div><label>{{ t('access.description') }}</label><input v-model="groupForm.description" /></div>
        </div>
        <div>
          <label>{{ t('access.members') }}</label>
          <div class="flex flex-wrap gap-2">
            <button v-for="u in userList.filter(x => !x.is_admin)" :key="u.id" type="button"
              class="px-3 py-1 rounded-full text-sm border transition-all"
              :class="groupForm.member_ids.includes(u.id) ? 'bg-brand-600 border-brand-500 text-white'
                      : 'bg-surface-600 border-surface-500 text-slate-400 hover:text-slate-200'"
              @click="toggle(groupForm.member_ids, u.id)">
              {{ groupForm.member_ids.includes(u.id) ? '✓ ' : '' }}{{ u.username }}
            </button>
          </div>
          <p class="text-xs text-slate-600 mt-2">{{ t('access.admin_hint') }}</p>
        </div>
        <div class="flex gap-3">
          <button class="btn-primary btn-sm" :disabled="groupSaving">{{ groupSaving ? t('common.saving') : t('common.save') }}</button>
          <button type="button" class="btn-secondary btn-sm" @click="groupForm = null">{{ t('common.cancel') }}</button>
        </div>
      </form>

      <div v-if="!groupList.length && !groupForm" class="text-slate-500 text-center py-10">{{ t('access.no_groups') }}</div>
      <div v-else class="grid sm:grid-cols-2 gap-3">
        <div v-for="g in groupList" :key="g.id" class="card">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="font-semibold text-slate-200">{{ g.name }}</div>
              <p v-if="g.description" class="text-xs text-slate-500 mt-0.5">{{ g.description }}</p>
            </div>
            <span class="badge-green flex-shrink-0">🦎 {{ g.animal_count }}</span>
          </div>
          <div class="text-xs text-slate-500 mt-3 mb-1">{{ t('access.members') }}</div>
          <div class="flex flex-wrap gap-1 min-h-[1.5rem]">
            <span v-for="id in g.member_ids" :key="id" class="badge-gray">{{ userName[id] ?? '#' + id }}</span>
            <span v-if="!g.member_ids.length" class="text-xs text-slate-600">—</span>
          </div>
          <div class="flex gap-2 mt-4">
            <button class="btn-secondary btn-sm flex-1" @click="editGroup(g)">{{ t('common.edit') }}</button>
            <button class="btn-danger btn-sm" @click="deleteGroup(g)">🗑</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
