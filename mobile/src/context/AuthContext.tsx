import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { getUser, setUser, clearUser, setToken, clearToken } from '../services/storage';
import { useQueryClient } from '@tanstack/react-query';

interface AuthContextValue {
  user: any | null;
  loading: boolean;
  signIn: (token: string, user: any) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  signIn: async () => {},
  signOut: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const queryClient = useQueryClient();

  useEffect(() => {
    (async () => {
      const stored = await getUser();
      if (stored) setUserState(stored);
      setLoading(false);
    })();
  }, []);

  const signIn = useCallback(async (token: string, userData: any) => {
    await setToken(token);
    await setUser(userData);
    setUserState(userData);
  }, []);

  const signOut = useCallback(async () => {
    await clearToken();
    await clearUser();
    setUserState(null);
    queryClient.clear();
  }, [queryClient]);

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
