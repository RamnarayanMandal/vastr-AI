import React from 'react';
import { Image, StyleSheet, Text, TouchableOpacity, View, useColorScheme } from 'react-native';
import { colors, radius, spacing, typography, shadows } from '../theme';

interface ImageUploadCardProps {
  stepLabel: string;
  title: string;
  subtitle: string;
  uri: string | null;
  primaryLabel: string;
  secondaryLabel?: string;
  onPrimary: () => void;
  onSecondary?: () => void;
  onChange?: () => void;
  onRemove?: () => void;
  onRetake?: () => void;
}

export default function ImageUploadCard({
  stepLabel,
  title,
  subtitle,
  uri,
  primaryLabel,
  secondaryLabel,
  onPrimary,
  onSecondary,
  onChange,
  onRemove,
  onRetake,
}: ImageUploadCardProps) {
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  const cardBg = dark ? colors.darkSurface : colors.surface;
  const border = dark ? colors.darkBorder : colors.border;
  const textPrimary = dark ? colors.darkTextPrimary : colors.textPrimary;
  const textSecondary = dark ? colors.darkTextSecondary : colors.textSecondary;

  return (
    <View style={[styles.wrap, { backgroundColor: cardBg, borderColor: border }]}>
      <View style={styles.stepRow}>
        <View style={styles.stepBadge}>
          <Text style={styles.stepText}>{stepLabel}</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={[styles.title, { color: textPrimary }]}>{title}</Text>
          <Text style={[styles.subtitle, { color: textSecondary }]}>{subtitle}</Text>
        </View>
      </View>

      {uri ? (
        <View style={styles.previewArea}>
          <Image source={{ uri }} style={styles.previewImage} resizeMode="cover" />
          <View style={styles.imageOverlay}>
            <View style={styles.imageOverlayBadge}>
              <Text style={styles.imageOverlayText}>✓ Added</Text>
            </View>
          </View>
          <View style={styles.actions}>
            {onRetake && (
              <TouchableOpacity style={styles.actionBtn} onPress={onRetake}>
                <Text style={styles.actionText}>⟳ Retake</Text>
              </TouchableOpacity>
            )}
            {onChange && (
              <TouchableOpacity style={styles.actionBtn} onPress={onChange}>
                <Text style={styles.actionText}>⇄ Change</Text>
              </TouchableOpacity>
            )}
            {onRemove && (
              <TouchableOpacity style={styles.actionBtnDanger} onPress={onRemove}>
                <Text style={styles.actionTextDanger}>✕ Remove</Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
      ) : (
        <TouchableOpacity style={styles.uploadArea} onPress={onPrimary} activeOpacity={0.7}>
          <View style={styles.cameraCircle}>
            <Text style={styles.cameraIcon}>📷</Text>
          </View>
          <Text style={[styles.actionPrimary, { color: textPrimary }]}>{primaryLabel}</Text>
          {secondaryLabel && (
            <TouchableOpacity onPress={onSecondary} style={styles.secondaryTap}>
              <Text style={[styles.actionSecondary, { color: colors.accentDark }]}>{secondaryLabel}</Text>
            </TouchableOpacity>
          )}
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderRadius: radius.xl,
    borderWidth: 1,
    padding: spacing.md,
    ...shadows.card,
  },
  stepRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  stepBadge: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    borderRadius: radius.sm,
  },
  stepText: {
    color: colors.accent,
    fontSize: typography.fontSize.micro,
    fontWeight: '800',
    letterSpacing: 1,
  },
  title: {
    fontSize: typography.fontSize.subheading,
    fontWeight: '700',
  },
  subtitle: {
    fontSize: typography.fontSize.bodySmall,
    marginTop: 2,
  },
  uploadArea: {
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 200,
    borderRadius: radius.lg,
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: colors.accent,
    backgroundColor: colors.accentGlow,
    padding: spacing.lg,
  },
  cameraCircle: {
    width: 60,
    height: 60,
    borderRadius: radius.full,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  cameraIcon: { fontSize: 26 },
  actionPrimary: {
    fontSize: typography.fontSize.body,
    fontWeight: '700',
  },
  secondaryTap: {
    marginTop: spacing.sm,
  },
  actionSecondary: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  previewArea: {
    borderRadius: radius.lg,
    overflow: 'hidden',
  },
  previewImage: {
    width: '100%',
    height: 260,
  },
  imageOverlay: {
    position: 'absolute',
    top: spacing.sm,
    right: spacing.sm,
  },
  imageOverlayBadge: {
    backgroundColor: colors.success,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.full,
  },
  imageOverlayText: {
    color: '#fff',
    fontSize: typography.fontSize.micro,
    fontWeight: '700',
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.xs,
    gap: spacing.sm,
  },
  actionBtn: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.full,
    backgroundColor: colors.surfaceAlt,
  },
  actionText: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  actionBtnDanger: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.full,
    backgroundColor: colors.dangerSoft,
  },
  actionTextDanger: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '600',
    color: colors.danger,
  },
});
