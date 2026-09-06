import { Stack } from 'expo-router';

export default function CameraLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        presentation: 'fullScreenModal',
        animation: 'fade',
      }}
    >
      <Stack.Screen name="person" />
      <Stack.Screen name="fabric" />
    </Stack>
  );
}
