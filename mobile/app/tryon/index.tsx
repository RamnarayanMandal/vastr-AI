import React, { useEffect } from 'react';
import { useRouter } from 'expo-router';
import { useTryOn } from '../../src/context/TryOnContext';

export default function TryOnIndex() {
  const router = useRouter();
  const { draft, setDraft } = useTryOn();

  useEffect(() => {
    if (draft.garmentId && draft.personImageUri && draft.fabricImageUri) {
      router.replace('/review');
    } else if (draft.garmentId) {
      router.replace('/tryon/upload');
    } else {
      if (!draft.gender) {
        setDraft({ gender: 'WOMEN' });
      }
      router.replace('/tryon/garment');
    }
  }, []);

  return null;
}