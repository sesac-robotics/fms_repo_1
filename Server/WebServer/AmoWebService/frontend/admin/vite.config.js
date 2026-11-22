import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [vue()],
  publicDir: fileURLToPath(new URL("../../../../../maps", import.meta.url)),
  server: {
    host: "127.0.0.1",
    proxy: { "/api": process.env.AMO_API_URL || "http://127.0.0.1:18085" },
  },
});
