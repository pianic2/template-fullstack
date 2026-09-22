import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { configureApiClient } from '@template/api-client';
import { ThemeProvider } from '@personal-library/react-native-components';
import type { PropsWithChildren } from 'react';
import * as SecureStore from 'expo-secure-store';
import { refreshSession } from '../auth/tokens';
import { secureThemeStorage } from '../theme-storage';

const apiUrl = new URL(process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000');

configureApiClient({
  baseUrl: apiUrl.origin,
  accessToken: () => SecureStore.getItemAsync('product.access-token'),
  refreshAccessToken: refreshSession,
});

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 15_000 } },
});

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider persistTheme storage={secureThemeStorage} storageKey="product.theme">
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
}
