import { ref } from 'vue'
import de from './de'
import en from './en'

/*
 * Eigene Mini-i18n — kein externes Paket nötig.
 *
 * Neue Sprache hinzufügen:
 * 1. src/i18n/es.js anlegen (an de.js orientieren)
 * 2. Hier importieren: import es from './es'
 * 3. In 'messages' und 'languages' eintragen
 */

const messages = { de, en }

export const languages = {
  en: { name: 'English', short: 'EN', intl: 'en-GB' },
  de: { name: 'Deutsch', short: 'DE', intl: 'de-DE' },
}

function initialLocale() {
  try {
    const saved = localStorage.getItem('locale')
    if (saved && languages[saved]) return saved
  } catch { /* storage unavailable */ }
  // No saved choice: follow the browser language, fall back to English
  const nav = (navigator.languages || [navigator.language || '']).map(l => String(l).slice(0, 2).toLowerCase())
  return nav.find(l => languages[l]) || 'en'
}

export const locale = ref(initialLocale())
document.documentElement.lang = locale.value

function get(obj, path) {
  return path.split('.').reduce((o, k) => o?.[k], obj)
}

export function setLocale(lang) {
  if (!languages[lang]) return
  locale.value = lang
  try { localStorage.setItem('locale', lang) } catch { /* ignore */ }
  document.documentElement.lang = lang
}

export function useI18n() {
  function t(key, vars) {
    // Accessing locale.value makes Vue track reactivity automatically
    let s = get(messages[locale.value], key) ?? get(messages.en, key) ?? key
    if (vars && typeof s === 'string') {
      s = s.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? `{${k}}`))
    }
    return s
  }
  return { t, locale }
}

// Dummy Vue plugin — keeps import in main.js harmless
export default { install() {} }
