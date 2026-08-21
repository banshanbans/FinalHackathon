import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "./",
  build: {
    outDir: "dist/client",
    sourcemap: true,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          motion: ["gsap", "lenis"],
          react: ["react", "react-dom", "zustand"],
          three: [
            "three",
            "@react-three/fiber",
            "@react-three/drei",
            "@react-three/postprocessing",
            "postprocessing",
          ],
        },
      },
    },
  },
  optimizeDeps: {
    include: ["react", "react-dom/client", "three", "gsap", "lenis"],
  },
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 4190,
    strictPort: true,
    allowedHosts: ["terminal.local"],
    warmup: {
      clientFiles: ["./src/main.tsx"],
    },
  },
  test: {
    include: ["src/**/*.test.ts"],
  },
});
