import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AuthProvider } from '../src/context/AuthContext';
import { TryOnProvider } from '../src/context/TryOnContext';
import { QueryProvider } from '../src/query/QueryProvider';

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <QueryProvider>
        <AuthProvider>
          <TryOnProvider>
          <StatusBar style="light" />
          <Stack
            screenOptions={{
              headerShown: false,
              contentStyle: { backgroundColor: '#0D0B1A' },
            }}
          >
            <Stack.Screen name="index" />
          </Stack>
          </TryOnProvider>
        </AuthProvider>
      </QueryProvider>
    </SafeAreaProvider>
  );
}