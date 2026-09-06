import axios from 'axios';
import { getToken, clearToken, clearUser } from '../services/storage';
import { parseApiError } from './errors';

export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { Accept: 'application/json' },
});

apiClient.interceptors.request.use(async (config) => {
  const token = await getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const parsed = parseApiError(error);
    if (parsed.status === 401) {
      await clearToken();
      await clearUser();
    }
    return Promise.reject(parsed);
  },
);
