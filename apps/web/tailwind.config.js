/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#1a1a1e",
        row: "#222228",
        border: "#33333a",
      },
    },
  },
  plugins: [],
};
