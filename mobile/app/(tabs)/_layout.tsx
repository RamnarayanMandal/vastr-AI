import React from 'react';
import { Stack } from 'expo-router';
import { useColorScheme } from 'react-native';
import { colors } from '../../src/theme';

export default function TabsLayout() {
  const scheme = useColorScheme();
  const dark = scheme === 'dark';

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: dark ? colors.darkBackground : colors.background },
        animation: 'fade',
      }}
    >
      <Stack.Screen name="home" />
      <Stack.Screen name="history" />
      <Stack.Screen name="profile" />
    </Stack>
  );
}
