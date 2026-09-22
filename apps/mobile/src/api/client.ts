import { configureApiClient, getHealthLive, getUsersMe } from '@template/api-client';
import * as SecureStore from 'expo-secure-store';

const apiUrl = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';
const apiOrigin = new URL(apiUrl).origin;

configureApiClient({
  baseUrl: apiOrigin,
  accessToken: () => SecureStore.getItemAsync('product.access-token'),
});

export const api = {
  health: () => getHealthLive(),
  currentUser: () => getUsersMe(),
};
