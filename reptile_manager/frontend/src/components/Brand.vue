<script setup>
defineProps({ size: { type: Number, default: 34 } })
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 40 40" fill="none" aria-hidden="true">
    <rect x="0.5" y="0.5" width="39" height="39" rx="11" fill="rgb(var(--ink-850))" stroke="rgb(var(--line-strong))" />
    <path d="M10 28c0-6 5-8 10-8s10-2 10-8" stroke="rgb(var(--moss-400))" stroke-width="3.6" stroke-linecap="round" />
    <path d="M10 28c0 1.8 1.4 3 3.2 3H22" stroke="rgb(var(--moss-400))" stroke-opacity=".45" stroke-width="3.6" stroke-linecap="round" />
    <circle cx="29.6" cy="10.6" r="2.6" fill="rgb(var(--moss-300))" />
  </svg>
</template>
