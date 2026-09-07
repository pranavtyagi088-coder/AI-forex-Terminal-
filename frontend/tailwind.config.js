/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0a0b0f',
        panel: '#0d1117',
        card: '#161b22',
        border: '#1e2329',
        bull: '#00d4aa',
        bear: '#ff4757',
        neutralc: '#ffa502',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
