import { defineConfig } from "vite";

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: "index.html",
        admin: "admin.html",
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/admin": {
        target: "http://localhost:8000",
        bypass(req) {
          // Serve the admin page from Vite in dev; proxy only the admin API
          // routes (/admin/login, /admin/conversations, ...) to the backend.
          const path = (req.url ?? "").split("?")[0];
          if (path === "/admin" || path === "/admin/") {
            return "/admin.html";
          }
        },
      },
    },
  },
});
