/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./trading_text/main/templates/**/*.html",
    "./trading_text/main/static/main/js/**/*.js",
  ],
  corePlugins: {
    preflight: false,
  },
  theme: {
    screens: {
      sm: "640px",
      md: "768px",
      lg: "1024px",
      xl: "1280px",
    },
    extend: {
      colors: {
        ou: {
          blue: "#0034b8",
          navy: "#070d2f",
          line: "#d9dfeb",
          surface: "#f7f9fc",
        },
      },
      maxWidth: {
        app: "1180px",
        form: "760px",
        reading: "840px",
      },
    },
  },
  plugins: [],
};
