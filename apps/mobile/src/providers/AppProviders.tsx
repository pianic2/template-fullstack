import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@personal-library/react-native-components';
import type { PropsWithChildren } from 'react';
import { secureThemeStorage } from '../theme-storage';

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 15_000 } } });

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider persistTheme storage={secureThemeStorage} storageKey="product.theme">
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
}
