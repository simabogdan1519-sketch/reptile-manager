<script setup>
import { useI18n, languages, locale } from '@/i18n'
import PageHeader from '@/components/PageHeader.vue'
import Icon from '@/components/Icon.vue'
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { animals as animalsApi } from '@/api'
import { mediaUrl } from '@/utils/media'

const { t } = useI18n()

const route  = useRoute()
const router = useRouter()
const animal  = ref(null)
const loading = ref(true)
const canvasRef  = ref(null)
const rendering  = ref(false)

const cfg = ref({
  width_mm: 90, height_mm: 54,
  bg_color: '#1e2433', text_color: '#f1f5f9',
  accent_color: '#4ade80', border: true,
  border_color: '#4ade80', border_width: 1.5,
  corner_radius: 5,

  show_emoji: true, emoji: '🦎',
  show_name: true, show_species: true,
  show_morph: true, show_sex: true,
  show_dob: true, show_weight: false,
  custom_line1: '', custom_line2: '',

  // Haltungsbedingungen auf dem Schild
  show_temp: true, show_humidity: true,
  show_terrarium: true, show_substrate: false,
  show_uv: false,

  // Foto
  show_photo: false,

  qr_enabled: true, qr_content: '', qr_position: 'right',
  qr_target: 'browser',   // 'browser' | 'ha_app' | 'custom'
  export_dpi: 300,
})

const SIZE_PRESETS = [
  { label: '90×54',   w: 90,  h: 54  },
  { label: '85×55',   w: 85,  h: 55  },
  { label: '50×30',   w: 50,  h: 30  },
  { label: '70×42',   w: 70,  h: 42  },
  { label: '100×60',  w: 100, h: 60  },
  { label: t('label.a6_landscape'), w: 148, h: 105 },
]

const COLOR_PRESETS = [
  { label: t('label.dark_green'),  bg: '#1e2433', text: '#f1f5f9', accent: '#4ade80', border: '#4ade80' },
  { label: t('label.dark_blue'),  bg: '#1e2433', text: '#f1f5f9', accent: '#60a5fa', border: '#60a5fa' },
  { label: t('label.dark_orange'),bg: '#1a0f00', text: '#fde68a', accent: '#f97316', border: '#f97316' },
  { label: t('label.black_gold'), bg: '#070707', text: '#fbbf24', accent: '#fbbf24', border: '#a16207' },
  { label: t('label.white_green'),   bg: '#ffffff', text: '#1e293b', accent: '#16a34a', border: '#16a34a' },
  { label: t('label.white_purple'),   bg: '#faf5ff', text: '#1e293b', accent: '#9333ea', border: '#9333ea' },
  { label: t('label.white_black'),bg: '#ffffff', text: '#111111', accent: '#111111', border: '#374151' },
  { label: t('label.nature_brown'), bg: '#fefce8', text: '#3d1f00', accent: '#854d0e', border: '#a16207' },
]

const MM = 25.4

function roundRect(ctx, x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y,     x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x,     y + h, r)
  ctx.arcTo(x,     y + h, x,     y,     r)
  ctx.arcTo(x,     y,     x + w, y,     r)
  ctx.closePath()
}

function fitText(ctx, text, maxW) {
  if (!text || maxW <= 0) return ''
  if (ctx.measureText(text).width <= maxW) return text
  let t = text
  while (t.length > 0 && ctx.measureText(t + '…').width > maxW) t = t.slice(0, -1)
  return t + '…'
}

function loadImg(src, crossOrigin = false) {
  return new Promise((res) => {
    const img = new Image()
    if (crossOrigin) img.crossOrigin = 'anonymous'
    img.onload  = () => res(img)
    img.onerror = () => res(null)
    img.src = src
  })
}

async function qrDataURL(text, size, dark, light) {
  try {
    const QRCode = (await import('qrcode')).default
    return await QRCode.toDataURL(text, {
      width: size, margin: 1,
      errorCorrectionLevel: 'M',
      color: { dark, light },
    })
  } catch { return null }
}

async function draw(canvas, dpi) {
  const c = cfg.value
  const a = animal.value
  const W = Math.round((c.width_mm  / MM) * dpi)
  const H = Math.round((c.height_mm / MM) * dpi)
  canvas.width = W; canvas.height = H

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, W, H)

  const S  = dpi / MM   // px per mm
  const bw = c.border ? c.border_width * S : 0
  const r  = c.corner_radius * S

  // Background
  ctx.fillStyle = c.bg_color
  roundRect(ctx, 0, 0, W, H, r)
  ctx.fill()

  // Border
  if (c.border && bw > 0) {
    ctx.strokeStyle = c.border_color
    ctx.lineWidth = bw
    roundRect(ctx, bw/2, bw/2, W - bw, H - bw, r)
    ctx.stroke()
  }

  const PAD = 3 * S

  // ── Photo (left column) ──────────────────────────────────────────────────
  let photoW = 0
  if (c.show_photo && a.photo_url) {
    const photoImg = await loadImg(mediaUrl(a.photo_url), true)
    if (photoImg) {
      photoW = Math.min(H - PAD * 2 - bw * 2, W * 0.30)
      const px = bw + PAD
      const py = bw + PAD
      const ph = H - bw * 2 - PAD * 2

      // Clip + draw photo as rounded rect
      ctx.save()
      roundRect(ctx, px, py, photoW, ph, r * 0.6)
      ctx.clip()

      // Cover-fit the photo
      const scale = Math.max(photoW / photoImg.width, ph / photoImg.height)
      const sw = photoImg.width * scale
      const sh = photoImg.height * scale
      const sx = px + (photoW - sw) / 2
      const sy = py + (ph - sh) / 2
      ctx.drawImage(photoImg, sx, sy, sw, sh)
      ctx.restore()

      photoW += PAD  // gap after photo
    }
  }

  // ── QR Code (right column) ───────────────────────────────────────────────
  const IH    = H - PAD * 2 - bw * 2
  const qrSz  = c.qr_enabled ? Math.min(IH * 0.9, (W - photoW) * 0.35) : 0
  let qrImg = null
  if (c.qr_enabled && c.qr_content && qrSz > 10) {
    const url = await qrDataURL(c.qr_content, Math.round(qrSz), c.text_color, c.bg_color)
    if (url) qrImg = await loadImg(url)
  }
  if (qrImg) {
    const qrX = W - PAD - bw - qrSz
    const qrY = (H - qrSz) / 2
    ctx.drawImage(qrImg, qrX, qrY, qrSz, qrSz)
  }

  // ── Text column ──────────────────────────────────────────────────────────
  const textLeft = bw + PAD + photoW
  const textW    = W - bw * 2 - PAD * 2 - photoW - (c.qr_enabled ? qrSz + PAD : 0)
  let ty = bw + PAD

  if (c.show_emoji && c.emoji) {
    const eSz = Math.min(S * 7, H * 0.18)
    ctx.font = `${eSz}px serif`
    ctx.fillText(c.emoji, textLeft, ty + eSz * 0.88)
    ty += eSz + S * 1
  }
  if (c.show_name) {
    const nSz = Math.min(S * 6.5, textW * 0.25, H * 0.20)
    ctx.font = `bold ${nSz}px Arial, sans-serif`
    ctx.fillStyle = c.text_color
    ctx.fillText(fitText(ctx, a.name, textW), textLeft, ty + nSz)
    ty += nSz + S * 0.8
  }
  // Accent rule
  ctx.fillStyle = c.accent_color
  ctx.fillRect(textLeft, ty, textW * 0.65, Math.max(1, S * 0.5))
  ty += S * 2.2

  const bSz = Math.max(S * 2.5, Math.min(S * 3.5, H * 0.09))
  ctx.font = `${bSz}px Arial, sans-serif`

  if (c.show_species) {
    ctx.font = `italic ${bSz}px Arial, sans-serif`
    ctx.fillStyle = c.text_color + 'bb'
    ctx.fillText(fitText(ctx, a.species, textW), textLeft, ty + bSz)
    ty += bSz + S * 1.1
  }
  ctx.font = `${bSz}px Arial, sans-serif`

  if (c.show_morph && a.morph) {
    ctx.fillStyle = c.accent_color
    ctx.fillText(fitText(ctx, a.morph, textW), textLeft, ty + bSz)
    ty += bSz + S * 1.1
  }

  ctx.fillStyle = c.text_color + 'aa'
  const lines = []

  if (c.show_sex)    lines.push(a.sex === 'male' ? '1.0.0' : a.sex === 'female' ? '0.1.0' : '0.0.1')
  if (c.show_dob && a.date_of_birth) lines.push(`* ${new Date(a.date_of_birth).toLocaleDateString(languages[locale.value].intl)}`)
  if (c.show_weight && a.weight_g)   lines.push(`⚖ ${a.weight_g}g`)

  // Haltungsbedingungen
  if (c.show_temp && (a.temp_day_c || a.temp_night_c)) {
    let t = '🌡'
    if (a.temp_day_c)   t += ` ${a.temp_day_c}°C`
    if (a.temp_night_c) t += ` / ${a.temp_night_c}°C`
    lines.push(t)
  }
  if (c.show_humidity && (a.humidity_min || a.humidity_max)) {
    lines.push(`💧 ${a.humidity_min ?? '?'}–${a.humidity_max ?? '?'}%`)
  }
  if (c.show_terrarium && a.terrarium_size) lines.push(`📦 ${a.terrarium_size}`)
  if (c.show_substrate && a.substrate)      lines.push(`🌱 ${a.substrate}`)
  if (c.show_uv && a.uv_required !== null && a.uv_required !== undefined) {
    lines.push(a.uv_required ? '☀ UV' : '🚫 ' + t('common.not_required') + ' UV')
  }
  if (c.custom_line1) lines.push(c.custom_line1)
  if (c.custom_line2) lines.push(c.custom_line2)

  for (const line of lines) {
    if (ty + bSz > H - PAD - bw) break
    ctx.fillText(fitText(ctx, line, textW), textLeft, ty + bSz)
    ty += bSz + S * 1.1
  }
}

async function updatePreview() {
  if (!canvasRef.value || !animal.value) return
  rendering.value = true
  try {
    await draw(canvasRef.value, 96 * 2)
    const maxW  = Math.min(640, window.innerWidth - 48)
    const scale = Math.min(1, maxW / (canvasRef.value.width / 2))
    canvasRef.value.style.width  = `${(canvasRef.value.width  / 2) * scale}px`
    canvasRef.value.style.height = `${(canvasRef.value.height / 2) * scale}px`
  } finally {
    rendering.value = false
  }
}

async function downloadPNG() {
  const off = document.createElement('canvas')
  await draw(off, cfg.value.export_dpi)
  const a = document.createElement('a')
  a.download = `${animal.value.name.replace(/\s+/g, '_')}_schild.png`
  a.href = off.toDataURL('image/png')
  a.click()
}

function printLabel(onA4 = false) {
  const off = document.createElement('canvas')
  const mmW = cfg.value.width_mm
  const mmH = cfg.value.height_mm
  draw(off, 300).then(() => {
    const win = window.open('', '_blank', 'width=900,height=700')
    const dataUrl = off.toDataURL('image/png')
    const pageCSS = onA4
      ? `@page{size:A4 portrait;margin:10mm}
         html,body{width:190mm;margin:0;padding:0;overflow:hidden}
         .wrap{display:flex;align-items:flex-start;justify-content:flex-start}
         img{width:${mmW}mm;height:${mmH}mm;display:block}`
      : `@page{size:${mmW}mm ${mmH}mm;margin:0}
         html,body{width:${mmW}mm;height:${mmH}mm;margin:0;padding:0;overflow:hidden}
         img{width:${mmW}mm;height:${mmH}mm;display:block}`

    win.document.write(`<!DOCTYPE html>
<html><head><title>${animal.value.name}</title>
<style>*{box-sizing:border-box} ${pageCSS}</style>
</head><body><div class="wrap"><img src="${dataUrl}"/></div>
<script>window.onload=function(){setTimeout(function(){window.print();setTimeout(function(){window.close()},800)},400)}<\/script>
</body></html>`)
    win.document.close()
  })
}

const exportSize = computed(() => {
  const w = Math.round((cfg.value.width_mm  / MM) * cfg.value.export_dpi)
  const h = Math.round((cfg.value.height_mm / MM) * cfg.value.export_dpi)
  return `${w}×${h}px`
})
const activeSize = computed(() =>
  SIZE_PRESETS.find(p => p.w === cfg.value.width_mm && p.h === cfg.value.height_mm)?.label ?? 'Custom'
)

onMounted(async () => {
  const res = await animalsApi.get(route.params.id)
  animal.value = res.data

  const browserUrl = `${window.location.origin}${window.location.pathname.replace(/\/[^/]*$/, '')}/animals/${res.data.id}`
  const haAppUrl   = `homeassistant://navigate/hassio/ingress/local_reptile_manager#/animals/${res.data.id}`

  // Set initial QR content based on target
  function syncQr() {
    if (cfg.value.qr_target === 'browser')  cfg.value.qr_content = browserUrl
    if (cfg.value.qr_target === 'ha_app')   cfg.value.qr_content = haAppUrl
  }
  syncQr()

  // Keep QR content in sync when target changes
  watch(() => cfg.value.qr_target, (t) => {
    if (t !== 'custom') syncQr()
  })

  loading.value = false
  await nextTick()
  await updatePreview()
})

watch(cfg, updatePreview, { deep: true })

function sexNotation(sex) {
  if (sex === 'male')   return '1.0.0'
  if (sex === 'female') return '0.1.0'
  return '0.0.1'
}

</script>

<template>
  <div>
    <PageHeader :eyebrow="animal?.name" :title="t('label.title')" back @back="router.back()" />

    <div v-if="loading" class="card h-80 animate-pulse" />

    <div v-else class="grid xl:grid-cols-[1fr_360px] gap-6 items-start">

      <!-- Preview -->
      <div class="card xl:sticky xl:top-10">
        <h2 class="section-title mb-4">{{ t('label.preview') }}</h2>
        <div class="bg-ink-950 border border-line rounded-xl p-4 md:p-8 flex items-center justify-center min-h-[160px] relative">
          <div v-if="rendering" class="absolute inset-0 flex items-center justify-center text-fg-faint text-sm">{{ t('label.rendering') }}</div>
          <canvas ref="canvasRef" class="rounded shadow-2xl block" />
        </div>
        <p class="text-center text-xs text-fg-faint mt-3 num">
          {{ cfg.width_mm }}×{{ cfg.height_mm }} mm · {{ cfg.export_dpi }} dpi · {{ exportSize }}
        </p>
        <div class="flex gap-3 mt-4 justify-center flex-wrap">
          <button class="btn-primary btn-sm" @click="downloadPNG"><Icon name="download" :size="15" />{{ t('label.download_png') }}</button>
          <button class="btn-secondary btn-sm" @click="printLabel(false)"><Icon name="printer" :size="15" />{{ t('label.print_exact') }}</button>
          <button class="btn-secondary btn-sm" @click="printLabel(true)"><Icon name="printer" :size="15" />{{ t('label.print_a4') }}</button>
        </div>
        <div class="mt-3 flex items-center gap-3 justify-center">
          <span class="text-xs text-fg-faint">{{ t('label.dpi') }}</span>
          <select v-model.number="cfg.export_dpi" class="w-36 text-sm py-1">
            <option :value="150">150 dpi</option>
            <option :value="300">{{ t('label.dpi_print') }}</option>
            <option :value="600">600 dpi</option>
          </select>
        </div>
      </div>

      <!-- Config -->
      <div class="space-y-4">

        <!-- Size -->
        <div class="card">
          <h3 class="cfg-h">{{ t('label.size') }}</h3>
          <div class="flex flex-wrap gap-1.5 mb-3">
            <button v-for="p in SIZE_PRESETS" :key="p.label"
              class="btn-secondary btn-sm text-xs"
              :class="activeSize === p.label ? '!border-moss-400/60 !text-moss-300 !bg-moss-400/10' : ''"
              @click="cfg.width_mm = p.w; cfg.height_mm = p.h">
              {{ p.label }}
            </button>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div><label>{{ t('label.width_mm') }}</label><input type="number" v-model.number="cfg.width_mm" min="20" max="500" /></div>
            <div><label>{{ t('label.height_mm') }}</label><input type="number" v-model.number="cfg.height_mm" min="10" max="500" /></div>
          </div>
        </div>

        <!-- Colors -->
        <div class="card">
          <h3 class="cfg-h">{{ t('label.colors') }}</h3>
          <div class="flex flex-wrap gap-1.5 mb-3">
            <button v-for="p in COLOR_PRESETS" :key="p.label"
              class="px-2 py-1 rounded text-xs border-2 font-medium"
              :style="{ background: p.bg, color: p.text, borderColor: p.accent }"
              @click="cfg.bg_color=p.bg; cfg.text_color=p.text; cfg.accent_color=p.accent; cfg.border_color=p.border">
              {{ p.label }}
            </button>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div><label>{{ t('label.bg') }}</label>
              <div class="flex gap-2"><input type="color" v-model="cfg.bg_color" class="color-sw" /><input v-model="cfg.bg_color" class="flex-1 text-xs" /></div>
            </div>
            <div><label>{{ t('label.text_color') }}</label>
              <div class="flex gap-2"><input type="color" v-model="cfg.text_color" class="color-sw" /><input v-model="cfg.text_color" class="flex-1 text-xs" /></div>
            </div>
            <div><label>{{ t('label.accent') }}</label>
              <div class="flex gap-2"><input type="color" v-model="cfg.accent_color" class="color-sw" /><input v-model="cfg.accent_color" class="flex-1 text-xs" /></div>
            </div>
            <div>
              <label class="flex items-center gap-1.5"><input type="checkbox" v-model="cfg.border" /> {{ t('label.border') }}</label>
              <div class="flex gap-2 mt-1"><input type="color" v-model="cfg.border_color" class="color-sw" :disabled="!cfg.border" /><input type="number" v-model.number="cfg.border_width" min="0.5" max="5" step="0.5" class="flex-1 text-xs" :disabled="!cfg.border" placeholder="mm" /></div>
            </div>
          </div>
          <div class="mt-2">
            <label>{{ t('label.radius') }}: <span class="num">{{ cfg.corner_radius }} mm</span></label>
            <input type="range" v-model.number="cfg.corner_radius" min="0" max="20" step="0.5" class="w-full" />
          </div>
        </div>

        <!-- Content -->
        <div class="card">
          <h3 class="cfg-h">{{ t('label.content') }}</h3>

          <!-- Foto -->
          <label class="option mb-3" :class="{ on: cfg.show_photo }">
            <input type="checkbox" v-model="cfg.show_photo" class="w-4 h-4" />
            <span>
              <span class="option-title block">{{ t('label.show_photo') }}</span>
              <span v-if="!animal?.photo_url" class="option-desc block !text-heat-400">{{ t('label.no_photo') }}</span>
              <span v-else class="option-desc block">{{ t('label.photo_hint') }}</span>
            </span>
          </label>

          <!-- Emoji -->
          <div class="flex items-center gap-3 mb-3">
            <input type="checkbox" v-model="cfg.show_emoji" class="w-4 h-4" />
            <span class="text-sm text-fg-muted">{{ t('label.icon') }}</span>
            <input v-model="cfg.emoji" :disabled="!cfg.show_emoji" class="w-12 text-center text-lg px-1 py-0.5" />
          </div>

          <!-- Field checkboxes -->
          <div class="grid grid-cols-2 gap-x-4 gap-y-1.5 mb-3">
            <label v-for="[k,l] in [['show_name', t('animal.name')],['show_species', t('animal.species')],['show_morph', t('animal.morph')],['show_sex', t('animal.sex')],['show_dob', t('animal.dob')],['show_weight', t('animal.weight')]]"
              :key="k" class="flex items-center gap-2 text-sm cursor-pointer mb-0">
              <input type="checkbox" v-model="cfg[k]" class="w-3.5 h-3.5" />{{ l }}
            </label>
          </div>

          <!-- Haltungsbedingungen auf Schild -->
          <div class="border-t border-line pt-3 mb-3">
            <p class="eyebrow mb-2">{{ t('animal.husbandry') }}</p>
            <div class="grid grid-cols-2 gap-x-4 gap-y-1.5">
              <label v-for="[k,l] in [['show_temp', t('animal.temperature')],['show_humidity', t('animal.humidity')],['show_terrarium', t('animal.terrarium')],['show_substrate', t('animal.substrate')],['show_uv', 'UV']]"
                :key="k" class="flex items-center gap-2 text-sm cursor-pointer mb-0">
                <input type="checkbox" v-model="cfg[k]" class="w-3.5 h-3.5" />{{ l }}
              </label>
            </div>
          </div>

          <div class="space-y-2">
            <div><label>{{ t('label.custom_line1') }}</label><input v-model="cfg.custom_line1" :placeholder="t('label.custom_line1_ph')" /></div>
            <div><label>{{ t('label.custom_line2') }}</label><input v-model="cfg.custom_line2" :placeholder="t('label.custom_line2_ph')" /></div>
          </div>
        </div>

        <!-- QR -->
        <div class="card">
          <div class="flex items-center justify-between mb-3">
            <h3 class="cfg-h !mb-0">{{ t('label.qr') }}</h3>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="cfg.qr_enabled" class="w-4 h-4" />
              <span class="text-sm text-fg-muted">{{ t('common.enabled') }}</span>
            </label>
          </div>
          <div v-if="cfg.qr_enabled" class="space-y-3">
            <div>
              <label>{{ t('label.qr_target') }}</label>
              <div class="flex gap-2 mt-1">
                <button v-for="[val, label] in [['browser',t('label.qr_browser')],['ha_app',t('label.qr_ha_app')],['custom',t('label.qr_custom')]]"
                        :key="val" type="button"
                        class="flex-1 py-1.5 rounded-lg text-xs font-medium border transition-all"
                        :class="cfg.qr_target === val
                          ? 'bg-moss-400/10 border-moss-400/50 text-moss-300'
                          : 'bg-ink-850 border-line-strong text-fg-muted hover:text-fg'"
                        @click="cfg.qr_target = val">
                  {{ label }}
                </button>
              </div>
              <p class="text-xs text-fg-faint mt-1.5">
                <template v-if="cfg.qr_target === 'browser'">{{ t('label.qr_browser_hint') }}</template>
                <template v-else-if="cfg.qr_target === 'ha_app'">{{ t('label.qr_ha_hint') }}</template>
                <template v-else>{{ t('label.qr_custom_hint') }}</template>
              </p>
            </div>
            <div v-if="cfg.qr_target === 'custom'">
              <label>{{ t('label.qr_content') }}</label>
              <input v-model="cfg.qr_content" :placeholder="t('label.qr_placeholder')" />
            </div>
            <div v-else class="rounded-lg border border-line bg-ink-950 px-3 py-2 text-xs text-fg-muted font-mono break-all">
              {{ cfg.qr_content }}
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.cfg-h { @apply section-title mb-3; }
.color-sw { @apply w-10 h-9 p-0.5 rounded cursor-pointer flex-shrink-0 border-0 bg-transparent; }
</style>
