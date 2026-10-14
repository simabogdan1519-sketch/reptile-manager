import { locale, languages } from '@/i18n'

const intl = () => languages[locale.value]?.intl || 'en-GB'

export function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString(intl(), { day: '2-digit', month: 'short', year: 'numeric' })
}

export function fmtDateTime(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString(intl(), { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function fmtShort(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString(intl(), { day: '2-digit', month: 'short' })
}

/** Days between a date and now (floored). */
export function daysSince(d) {
  if (!d) return null
  return Math.floor((Date.now() - new Date(d).getTime()) / 86400000)
}

/** Relative time ("3 days ago") using Intl.RelativeTimeFormat. */
export function fmtRelative(d) {
  if (!d) return '—'
  const diff = (new Date(d).getTime() - Date.now()) / 1000
  const rtf = new Intl.RelativeTimeFormat(intl(), { numeric: 'auto' })
  const abs = Math.abs(diff)
  if (abs < 3600)     return rtf.format(Math.round(diff / 60), 'minute')
  if (abs < 86400)    return rtf.format(Math.round(diff / 3600), 'hour')
  if (abs < 86400*45) return rtf.format(Math.round(diff / 86400), 'day')
  if (abs < 86400*365)return rtf.format(Math.round(diff / (86400 * 30)), 'month')
  return rtf.format(Math.round(diff / (86400 * 365)), 'year')
}

/** Age from date of birth, as { value, unit } where unit is 'months' | 'years'. */
export function ageParts(dob) {
  if (!dob) return null
  const d = new Date(dob), now = new Date()
  const months = (now.getFullYear() - d.getFullYear()) * 12 + now.getMonth() - d.getMonth()
  if (months < 0) return null
  return months < 24 ? { value: months, unit: 'months' } : { value: +(months / 12).toFixed(1), unit: 'years' }
}

/** Herpetological sex notation (male.female.unknown). */
export function sexNotation(sex) {
  if (sex === 'male') return '1.0.0'
  if (sex === 'female') return '0.1.0'
  return '0.0.1'
}
export function sexBadge(sex) {
  return sex === 'male' ? 'badge-male' : sex === 'female' ? 'badge-female' : 'badge-unknown'
}
export function sexColor(sex) {
  return sex === 'male' ? 'text-male' : sex === 'female' ? 'text-female' : 'text-fg-faint'
}

export function foodLabel(f) {
  return [f.food_count > 1 ? `${f.food_count}×` : '', f.food_size, f.food_type].filter(Boolean).join(' ')
}

/** Current local time as value for <input type="datetime-local">. */
export function nowLocalInput() {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

export function errorMessage(e) {
  const d = e?.response?.data?.detail
  if (Array.isArray(d)) return d.map(x => x.msg).join(', ')
  return d || e?.message || 'Error'
}
