import { apiClient } from './client';
import { AuthResponse, User } from './types';

export async function login(identifier: string, password: string): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/login', { identifier, password });
  return data;
}

export async function register(input: { full_name: string; email: string; mobile: string; password: string }): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/register', input);
  return data;
}

export async function me(): Promise<User> {
  const { data } = await apiClient.get<User>('/auth/me');
  return data;
}

export async function forgotPassword(email: string): Promise<{ message: string }> {
  const { data } = await apiClient.post<{ message: string }>('/auth/forgot-password', { email });
  return data;
}

export async function resetPassword(otp: string, new_password: string): Promise<{ message: string }> {
  const { data } = await apiClient.post<{ message: string }>('/auth/reset-password', { otp, new_password });
  return data;
}
