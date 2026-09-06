import { Stack } from 'expo-router';

export default function TryOnLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: '#FAF8F5' },
        animation: 'slide_from_right',
      }}
    >
      <Stack.Screen name="index" />
      <Stack.Screen name="garment" />
      <Stack.Screen name="style" />
      <Stack.Screen name="upload" />
    </Stack>
  );
}