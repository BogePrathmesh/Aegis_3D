/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "primary": "#22C55E",
        "on-primary": "#ffffff",
        "surface": "#f7f9fb",
        "on-surface": "#191c1e",
        "on-surface-variant": "#3d4a3d",
        "outline-variant": "#bccbb9",
        "surface-container-low": "#f2f4f6",
        "surface-container-lowest": "#ffffff"
      },
      borderRadius: {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "2xl": "1rem",
        "3xl": "1.5rem",
        "full": "9999px"
      },
      fontFamily: {
        // As requested: No italics, replace with Helvetica Pro.
        // We Use a stack that starts with Helvetica Pro (commercial font) then falls back.
        "headline": ["Helvetica Neue", "Helvetica Pro", "Helvetica", "Arial", "sans-serif"],
        "body": ["Helvetica Neue", "Helvetica Pro", "Helvetica", "Arial", "sans-serif"],
        "label": ["Helvetica Neue", "Helvetica Pro", "Helvetica", "Arial", "sans-serif"]
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      },
      animation: {
        'fade-in': 'fade-in 0.6s ease-out forwards',
      }
    },
  },
  plugins: [],
}
