import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
  useColorScheme,
} from 'react-native';
import { colors, radius, spacing, typography, shadows } from '../theme';

type Variant = 'primary' | 'accent' | 'outline' | 'ghost' | 'danger';

interface AppButtonProps {
  title: string;
  onPress: () => void;
  variant?: Variant;
  disabled?: boolean;
  loading?: boolean;
  icon?: React.ReactNode;
  style?: object;
  fullWidth?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export default function AppButton({
  title,
  onPress,
  variant = 'primary',
  disabled = false,
  loading = false,
  icon,
  style,
  fullWidth = true,
  size = 'md',
}: AppButtonProps) {
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  const isDisabled = disabled || loading;

  const bg = {
    primary: colors.primary,
    accent: colors.accent,
    outline: 'transparent',
    ghost: 'transparent',
    danger: colors.danger,
  }[variant];

  const fg = {
    primary: colors.textOnDark,
    accent: colors.primary,
    outline: dark ? colors.darkTextPrimary : colors.textPrimary,
    ghost: colors.accent,
    danger: colors.textOnDark,
  }[variant];

  const border = variant === 'outline'
    ? (dark ? colors.darkBorder : colors.border)
    : variant === 'accent'
    ? colors.accent
    : undefined;

  const sizeStyles = {
    sm: { paddingVertical: 10, paddingHorizontal: spacing.md, minHeight: 40 },
    md: { paddingVertical: spacing.md, paddingHorizontal: spacing.lg, minHeight: 52 },
    lg: { paddingVertical: 18, paddingHorizontal: spacing.xl, minHeight: 58 },
  }[size];

  const fontSize = size === 'sm' ? typography.fontSize.bodySmall : typography.fontSize.body;

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.base,
        sizeStyles,
        { backgroundColor: bg, borderColor: border },
        fullWidth && styles.fullWidth,
        pressed && !isDisabled && styles.pressed,
        isDisabled && styles.disabled,
        variant === 'accent' && shadows.accent,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={fg} size="small" />
      ) : (
        <View style={styles.row}>
          {icon}
          <Text style={[styles.label, { color: fg, fontSize }]}>{title}</Text>
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: radius.full,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fullWidth: {
    width: '100%',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
  },
  label: {
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  pressed: {
    opacity: 0.85,
    transform: [{ scale: 0.98 }],
  },
  disabled: {
    opacity: 0.45,
  },
});
