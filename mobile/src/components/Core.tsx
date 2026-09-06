import React from 'react';
import { StyleSheet, Text, View, useColorScheme } from 'react-native';
import { colors, radius, spacing, typography, shadows } from '../theme';

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
}

export function SectionHeader({ title, subtitle, right }: SectionHeaderProps) {
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  return (
    <View style={styles.row}>
      <View style={{ flex: 1 }}>
        <Text style={[styles.title, { color: dark ? colors.darkTextPrimary : colors.textPrimary }]}>
          {title}
        </Text>
        {subtitle ? (
          <Text style={[styles.subtitle, { color: dark ? colors.darkTextSecondary : colors.textSecondary }]}>
            {subtitle}
          </Text>
        ) : null}
      </View>
      {right}
    </View>
  );
}

export function Screen({
  children,
  padded = true,
  style,
}: {
  children: React.ReactNode;
  padded?: boolean;
  style?: object;
}) {
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  return (
    <View
      style={[
        styles.screen,
        { backgroundColor: dark ? colors.darkBackground : colors.background },
        padded && styles.padded,
        style,
      ]}
    >
      {children}
    </View>
  );
}

export function Card({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: object;
}) {
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: dark ? colors.darkSurface : colors.surface,
          borderColor: dark ? colors.darkBorder : colors.border,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

export function Chip({
  label,
  active = false,
  onPress,
}: {
  label: string;
  active?: boolean;
  onPress?: () => void;
}) {
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  return (
    <View
      style={[
        styles.chip,
        {
          backgroundColor: active
            ? colors.primary
            : dark
            ? colors.darkSurface
            : colors.surface,
          borderColor: active
            ? colors.primary
            : dark
            ? colors.darkBorder
            : colors.border,
        },
      ]}
    >
      <Text
        style={[
          styles.chipText,
          {
            color: active
              ? colors.textOnDark
              : dark
              ? colors.darkTextSecondary
              : colors.textSecondary,
          },
        ]}
      >
        {label}
      </Text>
    </View>
  );
}

export function Badge({
  count,
  size = 'sm',
}: {
  count: number;
  size?: 'sm' | 'md';
}) {
  const s = size === 'sm' ? 18 : 24;
  return (
    <View style={[styles.badge, { width: s, height: s, borderRadius: s / 2 }]}>
      <Text style={[styles.badgeText, { fontSize: size === 'sm' ? 10 : 12 }]}>
        {count > 99 ? '99+' : count}
      </Text>
    </View>
  );
}

export function EmptyState({
  emoji,
  title,
  subtitle,
  action,
}: {
  emoji: string;
  title: string;
  subtitle: string;
  action?: React.ReactNode;
}) {
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  return (
    <View style={styles.empty}>
      <View style={[styles.emptyIconWrap, { backgroundColor: dark ? colors.darkSurfaceAlt : colors.accentSoft }]}>
        <Text style={styles.emptyEmoji}>{emoji}</Text>
      </View>
      <Text style={[styles.emptyTitle, { color: dark ? colors.darkTextPrimary : colors.textPrimary }]}>
        {title}
      </Text>
      <Text style={[styles.emptySub, { color: dark ? colors.darkTextSecondary : colors.textSecondary }]}>
        {subtitle}
      </Text>
      {action}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  padded: { paddingHorizontal: spacing.lg },
  card: {
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.md,
    ...shadows.card,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    marginVertical: spacing.md,
  },
  title: {
    fontSize: typography.fontSize.heading,
    fontWeight: '700',
  },
  subtitle: {
    fontSize: typography.fontSize.bodySmall,
    marginTop: spacing.xs,
  },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.full,
    borderWidth: 1,
  },
  chipText: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '600',
  },
  badge: {
    backgroundColor: colors.danger,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: {
    color: '#fff',
    fontWeight: '700',
  },
  empty: {
    alignItems: 'center',
    paddingVertical: spacing.xxxl,
    paddingHorizontal: spacing.xl,
  },
  emptyIconWrap: {
    width: 80,
    height: 80,
    borderRadius: radius.full,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  emptyEmoji: { fontSize: 36 },
  emptyTitle: {
    fontSize: typography.fontSize.heading,
    fontWeight: '700',
    textAlign: 'center',
  },
  emptySub: {
    fontSize: typography.fontSize.bodySmall,
    textAlign: 'center',
    marginTop: spacing.sm,
    maxWidth: 280,
  },
});
