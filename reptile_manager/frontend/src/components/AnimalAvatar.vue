<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import { mediaUrl } from '@/utils/media'
const props = defineProps({ animal: Object, size: { type: String, default: 'w-11 h-11' }, rounded: { type: String, default: 'rounded-xl' } })
const initials = computed(() => (props.animal?.name || '?').slice(0, 2).toUpperCase())
</script>

<template>
  <div class="relative flex-shrink-0 overflow-hidden border border-line-strong bg-ink-800 grid place-items-center"
       :class="[size, rounded]">
    <img v-if="animal?.photo_url" :src="mediaUrl(animal.photo_url)" :alt="animal.name" class="w-full h-full object-cover" />
    <span v-else class="font-display font-semibold text-fg-muted text-[13px]">{{ initials }}</span>
  </div>
</template>
