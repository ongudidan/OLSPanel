/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './whm/templates/**/*.html',
    './users/templates/**/*.html',
    './media/js/**/*.js',
    './templates/**/*.html',
    '../extra/**/*.pl',
    '../../olspanel-plugin-*/**/*.html',
    '../../olspanel-plugin-*/**/*.pl',
    '../../olspanel-plugin-*/**/*.js',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      colors: {
        brand: 'var(--brand-color, #ef6d19)',
        'brand-hover': 'var(--brand-hover, #d85d10)',
        'brand-light': 'rgba(239, 109, 25, 0.08)',
      },
      boxShadow: {
        'xs': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
      }
    },
  },
  plugins: [],
  corePlugins: {
    preflight: true,
  }
}
