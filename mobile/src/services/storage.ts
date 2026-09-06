import AsyncStorage from '@react-native-async-storage/async-storage';

const TOKEN_KEY = 'vastrai_token';
const USER_KEY = 'vastrai_user';
const DRAFT_KEY = 'vastrai_draft';
const HISTORY_KEY = 'vastrai_history';

export async function getToken(): Promise<string | null> {
  return AsyncStorage.getItem(TOKEN_KEY);
}

export async function setToken(token: string): Promise<void> {
  await AsyncStorage.setItem(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await AsyncStorage.removeItem(TOKEN_KEY);
}

export async function getUser(): Promise<any | null> {
  const raw = await AsyncStorage.getItem(USER_KEY);
  try {
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export async function setUser(user: any): Promise<void> {
  await AsyncStorage.setItem(USER_KEY, JSON.stringify(user));
}

export async function clearUser(): Promise<void> {
  await AsyncStorage.removeItem(USER_KEY);
}

export async function getDraft(): Promise<any | null> {
  const raw = await AsyncStorage.getItem(DRAFT_KEY);
  try {
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export async function setDraft(draft: any): Promise<void> {
  await AsyncStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
}

export async function clearDraft(): Promise<void> {
  await AsyncStorage.removeItem(DRAFT_KEY);
}

export async function getHistory(): Promise<any[]> {
  const raw = await AsyncStorage.getItem(HISTORY_KEY);
  try {
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export async function setHistory(items: any[]): Promise<void> {
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(items));
}

export async function addToHistory(item: any): Promise<void> {
  const current = await getHistory();
  await setHistory([item, ...current]);
}
