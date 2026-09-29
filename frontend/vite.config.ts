import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Built into dist/ and served by the voice API at /console/ (behind the team password).
// For development: `npm run dev` and open http://localhost:5173/console/ while the API runs
// on port 8000; API calls are forwarded there.
export default defineConfig({
  base: "/console/",
  plugins: [react(), tailwindcss()],
  server: {
    proxy: { "/console/api": "http://localhost:8000" },
  },
});
