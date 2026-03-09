module.exports = {
  darkMode: 'class',
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "primary": "#3b82f6",
        "primary-hover": "#2563eb",
        "primary-dark": "#2563eb",
        "background-light": "#eff6ff",
        "background-dark": "#0f172a",
        "surface-light": "#ffffff",
        "surface-dark": "#1e293b",
        "text-heading": "#1e3a8a",
        "text-primary-light": "#1e293b",
        "text-primary-dark": "#f1f5f9",
        "text-secondary-light": "#64748b",
        "text-secondary-dark": "#94a3b8",
        "text-body": "#334155",
        "text-muted": "#64748b",
        "border-light": "#dbeafe",
        "border-medium": "#bfdbfe",
        "border-dark": "#334155",
      },
      fontFamily: {
        "display": ["Inter", "sans-serif"],
        "body": ["Inter", "sans-serif"]
      },
      borderRadius: {
        "DEFAULT": "0.5rem",
        "lg": "1rem",
        "xl": "1.5rem",
        "full": "9999px"
      },
      keyframes: {
        'fade-in-down': {
          '0%': {
            opacity: '0',
            transform: 'translateY(-10px)'
          },
          '100%': {
            opacity: '1',
            transform: 'translateY(0)'
          },
        }
      },
      animation: {
        'fade-in-down': 'fade-in-down 0.5s ease-out',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
