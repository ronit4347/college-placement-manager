/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#202d3a',
        muted: '#697887',
        canvas: '#f4f6f8',
        brand: '#176b68',
      },
      boxShadow: {
        panel: '0 8px 30px rgba(16, 24, 40, 0.05)',
      },
    },
  },
  plugins: [],
}
