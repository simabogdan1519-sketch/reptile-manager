<script setup>
import Icon from './Icon.vue'
defineProps({ icon: { type: String, default: 'reptile' }, title: String, text: String })
</script>

<template>
  <div class="flex flex-col items-center justify-center text-center py-14 px-6">
    <div class="relative mb-4">
      <div class="absolute inset-0 rounded-2xl bg-moss-400/10 blur-xl" />
      <div class="relative w-14 h-14 rounded-2xl border border-line-strong bg-ink-850 grid place-items-center text-moss-400">
        <Icon :name="icon" :size="26" />
      </div>
    </div>
    <p class="font-display text-lg font-semibold text-fg">{{ title }}</p>
    <p v-if="text" class="text-sm text-fg-muted mt-1 max-w-sm">{{ text }}</p>
    <div v-if="$slots.default" class="mt-5"><slot /></div>
  </div>
</template>
