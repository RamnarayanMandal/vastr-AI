import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getDraft, setDraft as persistDraft, clearDraft } from '../services/storage';
import { UploadProgressHandler } from '../api/upload.api';
import { useCreateTryOnMutation, useUploadFabricMutation, useUploadPersonMutation } from '../hooks/mutations';
import { TryOnDraft } from '../types';

const EMPTY: TryOnDraft = {
  gender: 'MEN',
  garmentId: null,
  styleId: null,
  personImageUri: null,
  fabricImageUri: null,
  personImageUrl: null,
  fabricImageUrl: null,
  personImageId: null,
  fabricImageId: null,
  jobId: null,
  resultUrl: null,
  status: 'IDLE',
  error: null,
};

interface TryOnContextValue {
  draft: TryOnDraft;
  setDraft: (patch: Partial<TryOnDraft>) => Promise<void>;
  reset: () => Promise<void>;
  uploadPerson: (uri: string, onProgress?: UploadProgressHandler) => Promise<void>;
  uploadFabric: (uri: string, onProgress?: UploadProgressHandler) => Promise<void>;
  generate: () => Promise<string>;
}

const TryOnContext = createContext<TryOnContextValue>({
  draft: EMPTY,
  setDraft: async () => {},
  reset: async () => {},
  uploadPerson: async () => {},
  uploadFabric: async () => {},
  generate: async () => '',
});

export function TryOnProvider({ children }: { children: React.ReactNode }) {
  const [draft, setDraftState] = useState<TryOnDraft>(EMPTY);
  const createTryOnMutation = useCreateTryOnMutation();
  const uploadPersonMutation = useUploadPersonMutation();
  const uploadFabricMutation = useUploadFabricMutation();

  useEffect(() => {
    (async () => {
      const stored = await getDraft();
      if (stored) setDraftState({ ...EMPTY, ...stored });
    })();
  }, []);

  const setDraft = useCallback(async (patch: Partial<TryOnDraft>) => {
    setDraftState((prev) => {
      const next = { ...prev, ...patch };
      persistDraft(next);
      return next;
    });
  }, []);

  const reset = useCallback(async () => {
    setDraftState(EMPTY);
    await clearDraft();
  }, []);

  const uploadPerson = useCallback(async (uri: string, onProgress?: UploadProgressHandler) => {
    setDraftState((prev) => ({ ...prev, status: 'UPLOADING_PERSON' as const, personImageUri: uri }));
    try {
      const res = await uploadPersonMutation.mutateAsync({ uri, onProgress });
      setDraftState((prev) => {
        const next = {
          ...prev,
          personImageId: res.image_id,
          personImageUrl: res.url || null,
          status: 'PERSON_UPLOADED' as const,
        };
        persistDraft(next);
        return next;
      });
    } catch (e: any) {
      setDraftState((prev) => ({ ...prev, status: 'FAILED' as const, error: e.message }));
      throw e;
    }
  }, [uploadPersonMutation]);

  const uploadFabric = useCallback(async (uri: string, onProgress?: UploadProgressHandler) => {
    setDraftState((prev) => ({ ...prev, status: 'UPLOADING_FABRIC' as const, fabricImageUri: uri }));
    try {
      const res = await uploadFabricMutation.mutateAsync({ uri, onProgress });
      setDraftState((prev) => {
        const next = {
          ...prev,
          fabricImageId: res.image_id,
          fabricImageUrl: res.url || null,
          status: 'FABRIC_UPLOADED' as const,
        };
        persistDraft(next);
        return next;
      });
    } catch (e: any) {
      setDraftState((prev) => ({ ...prev, status: 'FAILED' as const, error: e.message }));
      throw e;
    }
  }, [uploadFabricMutation]);

  const generate = useCallback(async () => {
    const current = await getDraft();
    const activeJobId = current?.jobId ?? draft.jobId;
    const activeStatus = current?.status ?? draft.status;

    if (activeJobId && ['QUEUED', 'PROCESSING'].includes(activeStatus)) {
      return activeJobId;
    }

    const personImageId = current?.personImageId ?? draft.personImageId;
    const fabricImageId = current?.fabricImageId ?? draft.fabricImageId;
    const garmentId = current?.garmentId ?? draft.garmentId;
    const styleId = current?.styleId ?? draft.styleId;
    const gender = current?.gender ?? draft.gender;

    if (!personImageId || !fabricImageId || !garmentId || !styleId) {
      throw new Error('Missing required inputs.');
    }
    setDraftState((prev) => ({ ...prev, status: 'QUEUED' as const }));
    const job = await createTryOnMutation.mutateAsync({
      person_image_id: personImageId,
      fabric_image_id: fabricImageId,
      garment_type: garmentId,
      garment_style: styleId,
      gender,
    });
    setDraftState((prev) => {
      const next = { ...prev, jobId: job.id, status: 'QUEUED' as const };
      persistDraft(next);
      return next;
    });
    return job.id;
  }, [draft, createTryOnMutation]);

  return (
    <TryOnContext.Provider
      value={{ draft, setDraft, reset, uploadPerson, uploadFabric, generate }}
    >
      {children}
    </TryOnContext.Provider>
  );
}

export function useTryOn() {
  return useContext(TryOnContext);
}