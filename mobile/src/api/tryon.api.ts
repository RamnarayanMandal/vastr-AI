import { apiClient } from './client';
import { TryOnJob } from './types';

export interface CreateTryOnInput {
  person_image_id: string;
  fabric_image_id: string;
  garment_type: string;
  garment_style: string;
  gender: string;
}

export async function createTryOn(input: CreateTryOnInput): Promise<TryOnJob> {
  const { data } = await apiClient.post<TryOnJob>('/try-on', input);
  return data;
}

export async function getTryOnStatus(jobId: string): Promise<TryOnJob> {
  const { data } = await apiClient.get<TryOnJob>(`/try-on/${jobId}`);
  return data;
}

export async function getTryOnResult(jobId: string): Promise<{ result_url: string }> {
  const { data } = await apiClient.get<{ result_url: string }>(`/try-on/${jobId}/result`);
  return data;
}
