import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";
import { AppRouter } from "@/app/router";
import { AuthProvider } from "@/hooks/use-auth";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 15_000,
    },
  },
});

export function AppProviders({ children }: { children?: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          {children ?? <AppRouter />}
          <Toaster richColors position="top-right" />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
