import { apiClient } from './client';
import { NotificationItem } from './types';

export async function getNotifications(): Promise<NotificationItem[]> {
  const { data } = await apiClient.get<NotificationItem[]>('/notifications');
  return data;
}

export async function markNotificationRead(id: string): Promise<NotificationItem> {
  const { data } = await apiClient.patch<NotificationItem>(`/notifications/${id}/read`);
  return data;
}

export async function markAllNotificationsRead(): Promise<{ updated: boolean }> {
  const { data } = await apiClient.patch<{ updated: boolean }>('/notifications/read-all');
  return data;
}
