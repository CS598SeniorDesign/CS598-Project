module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        surface: "var(--surface)",
        "surface-hover": "var(--surface-hover)",
        navbar: "var(--navbar)",
        border: "var(--border)",
        muted: "var(--muted)",
        subtle: "var(--subtle)",
        input: "var(--input)",
        link: "var(--link)",
        primary: "var(--primary)",
        secondary: "var(--secondary)",
        accent: "var(--accent)",
        destructive: "var(--destructive)",
      },
    },
  },
  plugins: [],
};
