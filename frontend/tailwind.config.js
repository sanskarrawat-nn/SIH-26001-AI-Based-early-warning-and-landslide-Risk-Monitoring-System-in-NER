/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        command: {
          900: '#070d19',
          850: '#0c1527',
          800: '#111e36',
          700: '#1a2c4e',
          600: '#263d6b',
        },
        risk: {
          low: '#10b981',       // Emerald
          moderate: '#f59e0b',  // Amber
          high: '#f97316',      // Orange
          severe: '#ef4444',    // Rose-Red
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif']
      }
    },
  },
  plugins: [],
}
