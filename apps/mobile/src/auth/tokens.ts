import { postAuthToken, postAuthTokenLogout, postAuthTokenRefresh } from '@template/api-client';
import * as SecureStore from 'expo-secure-store';

const ACCESS_KEY = 'product.access-token';
const REFRESH_KEY = 'product.refresh-token';

export async function signIn(email: string, password: string): Promise<void> {
  const response = await postAuthToken({ email, password });
  const tokens = response.data;
  await SecureStore.setItemAsync(ACCESS_KEY, tokens.access);
  await SecureStore.setItemAsync(REFRESH_KEY, tokens.refresh);
}

export async function refreshSession(): Promise<boolean> {
  const refresh = await SecureStore.getItemAsync(REFRESH_KEY);
  if (!refresh) return false;
  try {
    const response = await postAuthTokenRefresh({ refresh });
    const tokens = response.data;
    await SecureStore.setItemAsync(ACCESS_KEY, tokens.access);
    await SecureStore.setItemAsync(REFRESH_KEY, tokens.refresh);
    return true;
  } catch {
    await clearTokens();
    return false;
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
  await Promise.all([SecureStore.deleteItemAsync(ACCESS_KEY), SecureStore.deleteItemAsync(REFRESH_KEY)]);
}
