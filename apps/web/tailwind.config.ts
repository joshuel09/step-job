import type { Config } from "tailwindcss";

/**
 * The 2018 Step Job palette, as tokens.
 *
 * The Android app had one light blue, white and charcoal. `brand` is that blue
 * as a scale so a gradient has somewhere to go; `ink` is the charcoal the
 * wordmark used for JOB. Nothing else is added — a second accent would be a
 * second brand.
 */
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          200: "#bae6fd",
          300: "#7dd3fc",
          400: "#38bdf8",
          500: "#1aa7e8",
          600: "#0284c7",
          700: "#036ba1",
          800: "#075985",
          900: "#0c4a6e",
        },
        ink: {
          DEFAULT: "#1c2530",
          soft: "#55606d",
          faint: "#8a93a0",
        },
      },
      fontFamily: {
        // No webfont. A Japanese interface that waits on a download shows the
        // wrong glyphs first, and the system faces are the ones the user's
        // own device renders best.
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Text",
          "Segoe UI",
          "Hiragino Sans",
          "Hiragino Kaku Gothic ProN",
          "Noto Sans JP",
          "Yu Gothic",
          "Meiryo",
          "sans-serif",
        ],
      },
      borderRadius: {
        card: "1.25rem",
      },
      boxShadow: {
        // Blue-tinted rather than grey: a neutral shadow on a blue wash reads
        // as dirt.
        glass: "0 8px 32px -8px rgb(3 105 161 / 0.18)",
        lift: "0 18px 48px -16px rgb(3 105 161 / 0.32)",
      },
      keyframes: {
        rise: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        rise: "rise 0.5s cubic-bezier(0.16, 1, 0.3, 1) both",
      },
    },
  },
  plugins: [],
} satisfies Config;
