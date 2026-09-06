import { apiClient } from './client';
import { CreditTransaction, Credits } from './types';

export async function getCredits(): Promise<Credits> {
  const { data } = await apiClient.get<Credits>('/credits');
  return data;
}

export async function getCreditHistory(): Promise<CreditTransaction[]> {
  const { data } = await apiClient.get<CreditTransaction[]>('/credits/history');
  return data;
}
