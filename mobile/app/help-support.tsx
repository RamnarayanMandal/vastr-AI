import React from 'react';
import { Linking, ScrollView, StyleSheet, Text, TouchableOpacity, useColorScheme, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { SUPPORT } from '../src/constants/support';
import { colors, radius, spacing, typography, shadows } from '../src/theme';

export default function HelpSupportScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';

  const bg = dark ? colors.darkBackground : colors.background;
  const surface = dark ? colors.darkSurface : colors.surface;
  const border = dark ? colors.darkBorder : colors.border;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
          <Text style={[styles.backArrow, { color: text }]}>‹</Text>
        </TouchableOpacity>
        <Text style={[styles.title, { color: text }]}>Help & Support</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={[styles.body, { color: secondary }]}>
          For help with your account or try-ons, contact the VastrAI support team.
        </Text>

        <View style={[styles.supportCard, { backgroundColor: surface, borderColor: border }]}>
          <Text style={[styles.label, { color: secondary }]}>Email</Text>
          <Text style={[styles.value, { color: text }]}>{SUPPORT.email}</Text>
          <View style={[styles.divider, { backgroundColor: border }]} />
          <Text style={[styles.label, { color: secondary }]}>Phone</Text>
          <Text style={[styles.value, { color: text }]}>{SUPPORT.phone}</Text>
        </View>

        <TouchableOpacity
          style={[styles.supportCta, { backgroundColor: colors.accent }]}
          activeOpacity={0.85}
          onPress={() => Linking.openURL(`mailto:${SUPPORT.email}`)}
        >
          <Text style={[styles.supportCtaLabel, { color: colors.primary }]}>Email Support</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.supportCta, { backgroundColor: 'transparent', borderColor: dark ? colors.darkBorder : colors.border }]}
          activeOpacity={0.85}
          onPress={() => Linking.openURL(`tel:${SUPPORT.phone}`)}
        >
          <Text style={[styles.supportCtaLabel, { color: text }]}>Call Support</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  backBtn: {
    width: 38,
    height: 38,
    borderRadius: radius.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backArrow: {
    fontSize: 26,
    fontWeight: '600',
    lineHeight: 30,
  },
  title: {
    fontSize: typography.fontSize.title,
    fontWeight: '800',
    letterSpacing: typography.letterSpacing.tight,
    flex: 1,
  },
  content: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  body: {
    fontSize: typography.fontSize.bodySmall,
    lineHeight: typography.lineHeight.bodySmall,
    marginBottom: spacing.lg,
  },
  supportCard: {
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.md,
    ...shadows.soft,
  },
  label: {
    fontSize: typography.fontSize.caption,
    fontWeight: '700',
    letterSpacing: typography.letterSpacing.wider,
    textTransform: 'uppercase',
  },
  value: {
    fontSize: typography.fontSize.body,
    fontWeight: '700',
    marginTop: 4,
  },
  divider: {
    height: 1,
    marginVertical: spacing.md,
  },
  supportCta: {
    marginTop: spacing.md,
    borderRadius: radius.full,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.md,
  },
  supportCtaLabel: {
    fontSize: typography.fontSize.body,
    fontWeight: '700',
  },
});