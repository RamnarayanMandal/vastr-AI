import { apiClient } from './client';

export async function deactivateAccount(): Promise<{ status: string }> {
  const { data } = await apiClient.post<{ status: string }>('/users/me/deactivate');
  return data;
}

export async function deleteAccount(): Promise<{ deleted: boolean }> {
  const { data } = await apiClient.delete<{ deleted: boolean }>('/users/me');
  return data;
}
