import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApiError } from '../api/errors';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: (failureCount, error) => {
        const status = error instanceof ApiError ? error.status : undefined;
        if (status !== undefined && [401, 403, 404, 422].includes(status)) return false;
        return failureCount < (status === 429 ? 1 : 2);
      },
      refetchOnWindowFocus: false,
    },
    mutations: { retry: false },
  },
});

export function QueryProvider({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
