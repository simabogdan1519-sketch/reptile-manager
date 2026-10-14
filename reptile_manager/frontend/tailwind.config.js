/** @type {import('tailwindcss').Config} */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Bricolage Grotesque Variable"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        sans:    ['"Instrument Sans Variable"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        // Semantic tokens (see style.css :root)
        ink:    { 950: v('ink-950'), 900: v('ink-900'), 850: v('ink-850'), 800: v('ink-800'), 700: v('ink-700') },
        line:   { DEFAULT: v('line'), strong: v('line-strong') },
        fg:     { DEFAULT: v('fg'), muted: v('fg-muted'), faint: v('fg-faint') },
        moss:   { 300: v('moss-300'), 400: v('moss-400'), 500: v('moss-500'), 600: v('moss-600'), ink: v('moss-ink') },
        heat:   { 400: v('heat-400'), 500: v('heat-500') },
        coral:  { 400: v('coral-400'), 500: v('coral-500') },
        lagoon: { 400: v('lagoon-400') },
        male:   v('male'),
        female: v('female'),
        // Legacy aliases so older markup keeps working
        surface: { 900: v('ink-950'), 800: v('ink-900'), 700: v('ink-850'), 600: v('ink-800'), 500: v('line-strong') },
        brand:   { 400: v('moss-400'), 500: v('moss-500'), 600: v('moss-600') },
      },
      borderRadius: { xl: '0.85rem', '2xl': '1.1rem' },
      boxShadow: {
        panel: '0 1px 0 0 rgb(255 255 255 / 0.03) inset, 0 12px 32px -18px rgb(0 0 0 / 0.7)',
        pop:   '0 24px 60px -20px rgb(0 0 0 / 0.8), 0 0 0 1px rgb(var(--line-strong))',
        glow:  '0 0 0 1px rgb(var(--moss-400) / 0.35), 0 8px 30px -10px rgb(var(--moss-400) / 0.35)',
      },
      keyframes: {
        rise: { '0%': { opacity: 0, transform: 'translateY(6px)' }, '100%': { opacity: 1, transform: 'none' } },
      },
      animation: { rise: 'rise .45s cubic-bezier(.2,.7,.2,1) both' },
    },
  },
  plugins: [],
}
