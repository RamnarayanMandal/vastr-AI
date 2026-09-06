import React from 'react';
import { Pressable, StyleSheet, Text, View, useColorScheme } from 'react-native';
import { useRouter, usePathname } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors, spacing, radius, typography, shadows } from '../theme';

const tabs = [
  { id: '/home', label: 'Home', icon: '🏠' },
  { id: '/tryon', label: 'Try On', icon: '✨', primary: true },
  { id: '/history', label: 'History', icon: '🕓' },
  { id: '/profile', label: 'Profile', icon: '👤' },
];

export default function BottomNav() {
  const router = useRouter();
  const pathname = usePathname();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  const insets = useSafeAreaInsets();

  const isActive = (id: string) => {
    if (id === '/home') return pathname === '/home' || pathname === '/';
    return pathname.startsWith(id);
  };

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: dark ? colors.darkSurface : colors.surface,
          borderTopColor: dark ? colors.darkBorder : colors.borderLight,
          paddingBottom: insets.bottom + 8,
        },
      ]}
    >
      {tabs.map((tab) => {
        const active = isActive(tab.id);
        if (tab.primary) {
          return (
            <Pressable key={tab.id} style={styles.tab} onPress={() => router.push('/tryon')}>
              <View style={[styles.primaryBtn, active && styles.primaryBtnActive]}>
                <Text style={styles.primaryIcon}>✨</Text>
              </View>
              <Text style={[styles.label, { color: colors.accent, fontWeight: '700' }]}>{tab.label}</Text>
            </Pressable>
          );
        }
        const fg = active
          ? (dark ? colors.darkTextPrimary : colors.primary)
          : (dark ? colors.darkTextSecondary : colors.textMuted);
        return (
          <Pressable key={tab.id} style={styles.tab} onPress={() => router.push(tab.id as never)}>
            <View style={[styles.iconWrap, active && { backgroundColor: dark ? colors.darkSurfaceAlt : colors.accentSoft }]}>
              <Text style={[styles.icon, { opacity: active ? 1 : 0.5 }]}>{tab.icon}</Text>
            </View>
            <Text style={[styles.label, { color: fg }]}>{tab.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    borderTopWidth: StyleSheet.hairlineWidth,
    paddingTop: spacing.sm,
    paddingHorizontal: spacing.xs,
    ...shadows.soft,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 2,
  },
  iconWrap: {
    width: 44,
    height: 30,
    borderRadius: radius.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
  icon: { fontSize: 20 },
  label: { fontSize: typography.fontSize.micro, fontWeight: '600' },
  primaryBtn: {
    width: 56,
    height: 48,
    borderRadius: radius.full,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: -26,
    ...shadows.accent,
  },
  primaryBtnActive: { backgroundColor: colors.accentDark },
  primaryIcon: { fontSize: 24 },
});
