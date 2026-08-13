import "@fontsource-variable/inter";
import "@fontsource-variable/noto-sans-sc";
import "maplibre-gl/dist/maplibre-gl.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { M34PresentationApp } from "./M34PresentationApp";
import "./presentation.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 12_000 } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <M34PresentationApp />
    </QueryClientProvider>
  </StrictMode>,
);
