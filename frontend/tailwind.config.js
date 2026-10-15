/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#FAF9F6",
        surface: {
          DEFAULT: "#FFFFFF",
          subtle: "#F4F2ED",
          border: "#E7E5E0",
        },
        ink: {
          primary: "#1C1917",
          secondary: "#78716C",
          muted: "#A8A29E",
        },
        accent: {
          primary: "#F59E0B",
          hover: "#D97706",
          soft: "#FEF3C7",
        },
        status: {
          warning: "#F59E0B",
          success: "#10B981",
          error: "#EF4444",
        },
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "Inter", "system-ui", "sans-serif"],
        serif: ["Newsreader", "Fraunces", "Georgia", "serif"],
      },
      borderRadius: {
        "3xl": "24px",
        "2xl": "16px",
        "xl": "12px",
      },
      boxShadow: {
        "subtle": "0 2px 16px rgba(28, 25, 23, 0.03)",
        "panel": "0 12px 32px rgba(28, 25, 23, 0.08)",
        "elevated": "0 20px 40px rgba(28, 25, 23, 0.12)",
      },
    },
  },
  plugins: [
    require("@tailwindcss/typography"),
  ],
}
