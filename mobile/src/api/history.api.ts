import { apiClient } from './client';
import { HistoryItem } from './types';

export async function getHistory(): Promise<HistoryItem[]> {
  const { data } = await apiClient.get<HistoryItem[]>('/history');
  return data;
}

export async function getHistoryItem(historyId: string): Promise<HistoryItem> {
  if (__DEV__) console.log(`[HISTORY_QUERY] historyId=${historyId}`);
  const { data } = await apiClient.get<HistoryItem>(`/history/${historyId}`);
  if (__DEV__) console.log(`[HISTORY_RESPONSE] historyId=${historyId} resultId=${data.id} resultUrl=${data.result_url}`);
  return data;
}
