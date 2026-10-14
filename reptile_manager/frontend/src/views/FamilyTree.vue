<script setup>
import { ref, h, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '@/i18n'
import { animals as animalsApi } from '@/api'
import { sexNotation, sexBadge } from '@/utils/format'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const treeData = ref(null)
const loading = ref(true)

onMounted(async () => {
  try { treeData.value = (await animalsApi.tree(route.params.id)).data }
  finally { loading.value = false }
})

// Small functional component for a tree node
const Node = (props) => {
  const a = props.animal
  if (!a) {
    return h('div', { class: 'node node-empty' }, [h('span', { class: 'eyebrow' }, props.role ? t('tree.' + props.role) : '—'), h('span', { class: 'text-fg-faint text-sm mt-1' }, t('tree.unknown'))])
  }
  return h('button', {
    class: ['node', props.main ? 'node-main' : '', a.sex === 'female' ? 'hover:border-female/50' : a.sex === 'male' ? 'hover:border-male/50' : ''],
    onClick: () => !props.main && router.push(`/animals/${a.id}`),
  }, [
    h('div', { class: 'flex items-center justify-between gap-2 w-full' }, [
      h('span', { class: 'eyebrow' }, props.role ? t('tree.' + props.role) : (a.tracking_id ? '#' + a.tracking_id : '')),
      h('span', { class: sexBadge(a.sex) }, sexNotation(a.sex)),
    ]),
    h('span', { class: ['font-display font-semibold text-fg truncate w-full text-left mt-1.5', props.main ? 'text-[20px]' : 'text-[15px]'] }, a.name),
    h('span', { class: 'text-[11.5px] text-fg-faint italic truncate w-full text-left' }, a.morph || a.species),
  ])
}
Node.props = ['animal', 'role', 'main']
</script>

<template>
  <div>
    <PageHeader :eyebrow="treeData?.animal?.name" :title="t('animal.tree')" back @back="router.back()" />

    <div v-if="loading" class="card h-80 animate-pulse" />

    <div v-else-if="treeData" class="card overflow-x-auto">
      <div class="min-w-[720px] py-4 flex flex-col items-center">
        <!-- Grandparents -->
        <div class="grid grid-cols-4 gap-4 w-full">
          <Node :animal="treeData.animal.mother?.mother" role="grandmother" />
          <Node :animal="treeData.animal.mother?.father" role="grandfather" />
          <Node :animal="treeData.animal.father?.mother" role="grandmother" />
          <Node :animal="treeData.animal.father?.father" role="grandfather" />
        </div>
        <div class="grid grid-cols-2 gap-4 w-full"><div class="bracket" /><div class="bracket" /></div>

        <!-- Parents -->
        <div class="grid grid-cols-2 gap-4 w-full">
          <div class="flex justify-center"><div class="w-[62%]"><Node :animal="treeData.animal.mother" role="mother" /></div></div>
          <div class="flex justify-center"><div class="w-[62%]"><Node :animal="treeData.animal.father" role="father" /></div></div>
        </div>
        <div class="w-full"><div class="bracket" /></div>

        <!-- Subject -->
        <div class="w-[300px]"><Node :animal="treeData.animal" main /></div>

        <!-- Offspring -->
        <template v-if="treeData.offspring.length">
          <div class="w-px h-8 bg-line-strong" />
          <p class="eyebrow mb-3">{{ t('tree.offspring', { n: treeData.offspring.length }) }}</p>
          <div class="flex flex-wrap gap-3 justify-center max-w-3xl">
            <div v-for="child in treeData.offspring" :key="child.id" class="w-[180px]"><Node :animal="child" /></div>
          </div>
        </template>
      </div>
    </div>

    <div v-else class="card"><EmptyState icon="tree" :title="t('common.not_found')" /></div>
  </div>
</template>

<style scoped>
:deep(.node) {
  @apply w-full min-h-[86px] flex flex-col items-start rounded-xl border border-line bg-ink-850 px-3.5 py-3 transition-all min-w-0;
}
:deep(button.node:not(.node-main)) { @apply hover:-translate-y-0.5 cursor-pointer; }
:deep(.node-empty) { @apply border-dashed bg-transparent; }
:deep(.node-main) {
  @apply border-moss-400/60 bg-moss-400/[0.07] px-5 py-4 cursor-default;
  box-shadow: 0 0 0 4px rgb(var(--moss-400) / .06), 0 20px 40px -20px rgb(var(--moss-400) / .4);
}
.bracket {
  @apply relative h-6 mx-[25%] mb-5 border-b border-x border-line-strong rounded-b-xl;
}
.bracket::after { content: ""; @apply absolute left-1/2 top-full w-px h-5 bg-line-strong; }
</style>
