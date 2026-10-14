<script setup>
import Icon from './Icon.vue'
defineProps({ open: Boolean, title: String, icon: String, width: { type: String, default: 'max-w-md' } })
defineEmits(['close'])
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-3 sm:p-6">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="$emit('close')" />
        <div class="modal-box relative w-full rounded-2xl bg-ink-900 shadow-pop max-h-[88vh] flex flex-col" :class="width">
          <div class="flex items-center gap-3 px-5 py-4 border-b border-line">
            <span v-if="icon" class="w-8 h-8 rounded-lg bg-moss-400/10 text-moss-400 grid place-items-center">
              <Icon :name="icon" :size="17" />
            </span>
            <h2 class="font-display font-semibold text-[17px] text-fg flex-1 min-w-0 truncate">{{ title }}</h2>
            <button class="icon-btn" @click="$emit('close')"><Icon name="x" :size="17" /></button>
          </div>
          <div class="overflow-y-auto p-5"><slot /></div>
          <div v-if="$slots.footer" class="px-5 py-4 border-t border-line flex gap-2 justify-end"><slot name="footer" /></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity .2s ease; }
.modal-enter-active .modal-box, .modal-leave-active .modal-box { transition: transform .25s cubic-bezier(.2,.7,.2,1); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal-box, .modal-leave-to .modal-box { transform: translateY(12px) scale(.98); }
</style>
