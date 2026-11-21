import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// OpenUI's package entry re-exports its whole library (code highlighting, date picker, markdown, zod), which would
// all ship on first load. Its components are also published as one ES module per file, so the app imports those
// directly through this alias. Pinned to @openuidev/react-ui 0.18.9: re-check the paths when upgrading.
const openuiParts = fileURLToPath(new URL("./node_modules/@openuidev/react-ui/dist/components", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: { alias: [{ find: /^@openuidev\/react-ui\/parts\//, replacement: `${openuiParts}/` }] },
  server: { proxy: { "/api": { target: "http://localhost:8000", rewrite: (p) => p.replace(/^\/api/, "") } } },
});
