import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { BrandingProvider } from "@/providers/BrandingProvider";
import { AppRouter } from "@/router";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrandingProvider>
        <AppRouter />
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "#1A1A24",
              color: "#E2E8F0",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "12px",
            },
          }}
        />
      </BrandingProvider>
    </QueryClientProvider>
  </StrictMode>
);
