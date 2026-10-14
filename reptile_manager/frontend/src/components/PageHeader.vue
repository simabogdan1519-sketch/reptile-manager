<script setup>
import Icon from './Icon.vue'
defineProps({
  title: String,
  eyebrow: String,
  subtitle: String,
  back: { type: [Boolean, String], default: false },
})
defineEmits(['back'])
</script>

<template>
  <header class="mb-6 md:mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between animate-rise">
    <div class="min-w-0 flex items-start gap-3">
      <button v-if="back" class="btn-secondary btn-icon mt-1 flex-shrink-0" :title="typeof back === 'string' ? back : ''"
              @click="$emit('back')">
        <Icon name="back" :size="17" />
      </button>
      <div class="min-w-0">
        <p v-if="eyebrow" class="eyebrow mb-1.5">{{ eyebrow }}</p>
        <h1 class="font-display text-[26px] md:text-[32px] leading-[1.1] font-semibold text-fg truncate">
          <slot name="title">{{ title }}</slot>
        </h1>
        <p v-if="subtitle || $slots.subtitle" class="text-fg-muted text-sm mt-1.5">
          <slot name="subtitle">{{ subtitle }}</slot>
        </p>
      </div>
    </div>
    <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2 md:justify-end">
      <slot name="actions" />
    </div>
  </header>
</template>
