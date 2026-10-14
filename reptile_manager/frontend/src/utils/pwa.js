import { ref } from 'vue'

/** Deferred `beforeinstallprompt` event → lets us show our own "Install app" button. */
export const canInstall = ref(false)
export const isStandalone = ref(
  window.matchMedia?.('(display-mode: standalone)').matches || window.navigator.standalone === true
)
export const online = ref(navigator.onLine)
let deferred = null

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault()
  deferred = e
  canInstall.value = true
})
window.addEventListener('appinstalled', () => {
  deferred = null
  canInstall.value = false
  isStandalone.value = true
})
window.addEventListener('online', () => (online.value = true))
window.addEventListener('offline', () => (online.value = false))

export async function promptInstall() {
  if (!deferred) return false
  deferred.prompt()
  const { outcome } = await deferred.userChoice
  deferred = null
  canInstall.value = false
  return outcome === 'accepted'
}

export function registerServiceWorker() {
  if (!('serviceWorker' in navigator) || !window.isSecureContext) return
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js', { scope: './' }).catch(() => { /* non-critical */ })
  })
}
