import { apiClient } from './client';
import { UploadResponse } from './types';

export type UploadProgressHandler = (progress: { loaded: number; total: number; percent: number }) => void;
export type UploadProgress = Parameters<UploadProgressHandler>[0];

async function upload(uri: string, path: string, onProgress?: UploadProgressHandler): Promise<UploadResponse> {
  const formData = new FormData();
  const filename = uri.split('/').pop() ?? 'image.jpg';
  formData.append('file', { uri, name: filename, type: filename.toLowerCase().endsWith('.png') ? 'image/png' : 'image/jpeg' } as unknown as Blob);
  const { data } = await apiClient.post<UploadResponse>(path, formData, {
    onUploadProgress: (event) => {
      const total = event.total ?? event.loaded;
      onProgress?.({ loaded: event.loaded, total, percent: total ? Math.round((event.loaded / total) * 100) : 0 });
    },
  });
  return data;
}

export const uploadPerson = (uri: string, onProgress?: UploadProgressHandler) => upload(uri, '/upload/person', onProgress);
export const uploadFabric = (uri: string, onProgress?: UploadProgressHandler) => upload(uri, '/upload/fabric', onProgress);
