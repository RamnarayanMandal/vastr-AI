import { useQuery } from '@tanstack/react-query';
import { getHistory, getHistoryItem } from '../api/history.api';
import { getNotifications } from '../api/notifications.api';
import { getCredits, getCreditHistory } from '../api/credits.api';
import { getTryOnResult, getTryOnStatus } from '../api/tryon.api';

export const useHistoryQuery = () => useQuery({ queryKey: ['history'], queryFn: getHistory });
export const useHistoryItemQuery = (historyId: string | undefined) => useQuery({ queryKey: ['history-detail', historyId], queryFn: () => getHistoryItem(historyId as string), enabled: Boolean(historyId) });
export const useNotificationsQuery = () => useQuery({ queryKey: ['notifications'], queryFn: getNotifications });
export const useCreditsQuery = () => useQuery({ queryKey: ['credits'], queryFn: getCredits });
export const useCreditHistoryQuery = () => useQuery({ queryKey: ['credits-history'], queryFn: getCreditHistory });
export const useTryOnStatusQuery = (jobId: string | undefined) => useQuery({
  queryKey: ['tryon-status', jobId],
  queryFn: () => getTryOnStatus(jobId as string),
  enabled: Boolean(jobId),
  refetchInterval: (query) => {
    const status = query.state.data?.status;
    return status === 'QUEUED' || status === 'PROCESSING' ? 2000 : false;
  },
});
export const useTryOnResultQuery = (jobId: string | undefined, enabled = true) => useQuery({ queryKey: ['tryon-result', jobId], queryFn: () => getTryOnResult(jobId as string), enabled: Boolean(jobId) && enabled });
