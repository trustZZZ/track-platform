import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// В dev-режиме проксируем /api на backend.
// VITE_PROXY_TARGET позволяет увести dev-прокси на другой порт (например,
// 8010), если :8000 занят docker-стеком другого/этого проекта.
// 127.0.0.1 вместо localhost: форсируем IPv4, чтобы не попасть в чужой
// IPv6-листенер (например, docker backend), когда порт разделён.
const proxyTarget = process.env.VITE_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "node",
    globals: true,
  },
});
