module.exports = {
  darkMode: 'class',
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "primary": "#3b82f6",
        "primary-dark": "#2563eb",
        "background-light": "#eff6ff",
        "background-dark": "#0f172a",
        "text-heading": "#1e3a8a",
        "text-body": "#334155",
        "text-muted": "#64748b",
        "border-light": "#dbeafe",
        "border-medium": "#bfdbfe",
      },
      fontFamily: {
        "display": ["Inter", "sans-serif"]
      },
      borderRadius: {
        "DEFAULT": "0.5rem",
        "lg": "1rem",
        "xl": "1.5rem",
        "full": "9999px"
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
