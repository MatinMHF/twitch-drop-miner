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
        twitch: {
          50: '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#9146ff', // Standard Twitch Purple
          600: '#772ce8',
          700: '#5c16c5',
          800: '#4c1d95',
          900: '#2e1065',
        },
      },
    },
  },
  plugins: [],
}
