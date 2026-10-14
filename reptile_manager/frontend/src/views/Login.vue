<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n, setLocale, languages } from '@/i18n'
import Brand from '@/components/Brand.vue'
import Icon from '@/components/Icon.vue'

const router = useRouter()
const auth = useAuthStore()
const { t, locale } = useI18n()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/dashboard')
  } catch {
    error.value = t('login.error')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen grid lg:grid-cols-[1.1fr_1fr]">
    <!-- Atmosphere panel -->
    <section class="hidden lg:flex relative overflow-hidden border-r border-line flex-col justify-between p-12">
      <div class="absolute inset-0 pointer-events-none">
        <div class="absolute -top-40 -left-40 w-[640px] h-[640px] rounded-full bg-moss-400/10 blur-3xl" />
        <div class="absolute bottom-[-200px] right-[-120px] w-[520px] h-[520px] rounded-full bg-heat-400/[0.06] blur-3xl" />
        <svg class="absolute inset-0 w-full h-full opacity-[0.07]" aria-hidden="true">
          <defs>
            <pattern id="scales" width="44" height="26" patternUnits="userSpaceOnUse">
              <path d="M0 13c5.5 0 11-5.7 11-13m0 0c0 7.3 5.5 13 11 13m0 0c5.5 0 11-5.7 11-13m0 0c0 7.3 5.5 13 11 13M11 26c0-7.3 5.5-13 11-13s11 5.7 11 13"
                    fill="none" stroke="rgb(var(--moss-300))" stroke-width="1" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#scales)" />
        </svg>
      </div>

      <div class="relative flex items-center gap-3">
        <Brand :size="40" />
        <span class="font-display font-bold text-xl text-fg">Reptile Manager</span>
      </div>

      <div class="relative max-w-md">
        <p class="eyebrow mb-4 text-moss-400/80">{{ t('login.eyebrow') }}</p>
        <h1 class="font-display text-[44px] leading-[1.02] font-semibold text-fg">
          {{ t('login.headline') }}
        </h1>
        <p class="text-fg-muted mt-5 text-[15px] leading-relaxed">{{ t('login.lede') }}</p>
        <div class="mt-8 flex flex-wrap gap-2">
          <span v-for="k in ['feeding','shed','egg','certificate']" :key="k" class="chip !cursor-default">
            <Icon :name="k" :size="15" class="text-moss-400" /> {{ t('login.features.' + k) }}
          </span>
        </div>
      </div>

      <p class="relative eyebrow">{{ t('login.footer') }}</p>
    </section>

    <!-- Form -->
    <section class="flex items-center justify-center p-6 sm:p-10">
      <div class="w-full max-w-[380px] animate-rise">
        <div class="lg:hidden flex items-center gap-3 mb-10">
          <Brand :size="38" />
          <span class="font-display font-bold text-xl text-fg">Reptile Manager</span>
        </div>

        <div class="flex items-center justify-between mb-8">
          <div>
            <h2 class="font-display text-[28px] font-semibold text-fg">{{ t('login.title') }}</h2>
            <p class="text-sm text-fg-muted mt-1">{{ t('login.subtitle') }}</p>
          </div>
          <div class="seg self-start">
            <button v-for="(lang, code) in languages" :key="code" :class="{ on: locale === code }"
                    type="button" @click="setLocale(code)">{{ lang.short }}</button>
          </div>
        </div>

        <form class="space-y-4" @submit.prevent="submit">
          <div>
            <label for="u">{{ t('access.username') }}</label>
            <input id="u" v-model="username" type="text" autocomplete="username" required autofocus />
          </div>
          <div>
            <label for="p">{{ t('access.password') }}</label>
            <input id="p" v-model="password" type="password" autocomplete="current-password" required />
          </div>

          <div v-if="error" class="alert-error"><Icon name="alert" :size="16" class="mt-0.5" />{{ error }}</div>

          <button type="submit" class="btn-primary btn-lg w-full" :disabled="loading">
            {{ loading ? t('login.signing_in') : t('login.submit') }}
            <Icon v-if="!loading" name="chevron" :size="17" />
          </button>
        </form>
      </div>
    </section>
  </div>
</template>
