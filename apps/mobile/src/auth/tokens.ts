import {
  ApiError,
  postAuthToken,
  postAuthTokenLogout,
  postAuthTokenRefresh,
} from '@template/api-client';
import * as SecureStore from 'expo-secure-store';

const ACCESS_KEY = 'product.access-token';
const REFRESH_KEY = 'product.refresh-token';
let refreshInFlight: Promise<string | null> | null = null;

export async function signIn(email: string, password: string): Promise<void> {
  const response = await postAuthToken({ email, password });
  const tokens = response.data;
  await SecureStore.setItemAsync(ACCESS_KEY, tokens.access);
  await SecureStore.setItemAsync(REFRESH_KEY, tokens.refresh);
}

export function refreshSession(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = rotateTokens().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

async function rotateTokens(): Promise<string | null> {
  const refresh = await SecureStore.getItemAsync(REFRESH_KEY);
  if (!refresh) return null;
  try {
    const response = await postAuthTokenRefresh(
      { refresh },
      { skipAccessToken: true, skipAuthRefresh: true },
    );
    const tokens = response.data;
    await SecureStore.setItemAsync(ACCESS_KEY, tokens.access);
    await SecureStore.setItemAsync(REFRESH_KEY, tokens.refresh);
    return tokens.access;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) await clearTokens();
    return null;
  }
}

export async function signOut(): Promise<void> {
  const refresh = await SecureStore.getItemAsync(REFRESH_KEY);
  try {
    if (refresh) await postAuthTokenLogout({ refresh });
  } finally {
    await clearTokens();
  }
}

async function clearTokens(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(ACCESS_KEY),
    SecureStore.deleteItemAsync(REFRESH_KEY),
  ]);
}
