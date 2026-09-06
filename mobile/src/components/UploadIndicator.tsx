import React from 'react';
import { ActivityIndicator, StyleSheet, Text, View, useColorScheme } from 'react-native';
import { UploadProgress } from '../api/upload.api';
import { colors, radius, spacing, typography } from '../theme';

interface UploadIndicatorProps {
  progress: UploadProgress;
  label?: string;
  dark?: boolean;
}

/** Full-screen loading overlay with a spinner and a real upload-percentage bar. */
export default function UploadIndicator({ progress, label = 'Uploading', dark = false }: UploadIndicatorProps) {
  const scheme = useColorScheme();
  const isDark = dark || scheme === 'dark';
  const pct = Math.min(100, Math.max(0, progress.percent));

  const bg = isDark ? 'rgba(18,16,27,0.72)' : 'rgba(13,11,26,0.55)';
  const surfaceBg = isDark ? colors.darkSurface : colors.background;
  const text = isDark ? colors.darkTextPrimary : colors.textPrimary;
  const track = isDark ? colors.darkBorder : colors.border;
  const fill = colors.accent;

  return (
    <View style={[StyleSheet.absoluteFill, styles.overlay, { backgroundColor: bg }]}>
      <View style={[styles.card, { backgroundColor: surfaceBg }]}>
        <ActivityIndicator size="large" color={fill} />
        <Text style={[styles.label, { color: text }]}>{label}…</Text>

        <View style={[styles.track, { backgroundColor: track }]}>
          <View style={[styles.fill, { width: `${pct}%`, backgroundColor: fill }]} />
        </View>

        <Text style={[styles.percent, { color: isDark ? colors.darkTextSecondary : colors.textSecondary }]}>
          {pct}%
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
  },
  card: {
    minWidth: 220,
    borderRadius: radius.xl,
    paddingVertical: spacing.xl,
    paddingHorizontal: spacing.lg,
    alignItems: 'center',
    gap: spacing.md,
  },
  label: {
    fontSize: typography.fontSize.body,
    fontWeight: '700',
  },
  track: {
    width: '100%',
    height: 8,
    borderRadius: radius.full,
    overflow: 'hidden',
    marginTop: spacing.xs,
  },
  fill: {
    height: '100%',
    borderRadius: radius.full,
  },
  percent: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '800',
    fontVariant: ['tabular-nums'],
  },
});
