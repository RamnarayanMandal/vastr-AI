import React from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, useColorScheme, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useCreditsQuery } from '../src/hooks/queries';
import { parseApiError } from '../src/api/errors';
import { colors, radius, spacing, typography, shadows } from '../src/theme';

export default function CreditsScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  const creditsQuery = useCreditsQuery();
  const data = creditsQuery.data;

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
        <Text style={[styles.title, { color: text }]}>AI Credits</Text>
      </View>

      {creditsQuery.isLoading ? (
        <View style={styles.state}>
          <Text style={{ color: secondary }}>Loading credits…</Text>
        </View>
      ) : creditsQuery.isError ? (
        <View style={styles.state}>
          <Text style={[styles.errorText, { color: colors.danger }]}>{parseApiError(creditsQuery.error).message}</Text>
          <TouchableOpacity style={[styles.retryCta, { backgroundColor: colors.accent }]} activeOpacity={0.85} onPress={() => creditsQuery.refetch()}>
            <Text style={styles.retryCtaText}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View style={[styles.balanceCard, { backgroundColor: colors.primary }]}>
            <Text style={styles.balanceLabel}>Available Balance</Text>
            <Text style={styles.balanceNumber}>{data?.balance ?? 0}</Text>
            <View style={styles.balanceDivider} />
            <View style={styles.balanceStats}>
              <View style={styles.balanceStat}>
                <Text style={styles.balanceStatValue}>{data?.total_used ?? 0}</Text>
                <Text style={styles.balanceStatLabel}>Used</Text>
              </View>
              <View style={styles.balanceStat}>
                <Text style={styles.balanceStatValue}>{data?.total_added ?? 0}</Text>
                <Text style={styles.balanceStatLabel}>Added</Text>
              </View>
            </View>
          </View>

          <Text style={[styles.sectionLabel, { color: secondary }]}>Usage History</Text>

          {(data?.transactions?.length ?? 0) === 0 ? (
            <View style={[styles.emptyCard, { backgroundColor: surface, borderColor: border }]}>
              <Text style={styles.emptyEmoji}>✦</Text>
              <Text style={[styles.emptyTitle, { color: text }]}>No transactions yet</Text>
              <Text style={[styles.emptySub, { color: secondary }]}>
                Your credit usage will appear here as you create try-ons.
              </Text>
            </View>
          ) : (
            <View style={styles.rows}>
              {(data?.transactions ?? []).map((item) => (
                <View key={item.id} style={[styles.row, { backgroundColor: surface, borderColor: border }]}>
                  <View style={[styles.amountBadge, { backgroundColor: item.amount > 0 ? colors.successSoft : colors.dangerSoft }]}>
                    <Text style={[styles.amountText, { color: item.amount > 0 ? colors.success : colors.danger }]}>
                      {item.amount > 0 ? '+' : ''}{item.amount}
                    </Text>
                  </View>
                  <View style={styles.rowInfo}>
                    <Text style={[styles.rowTitle, { color: text }]} numberOfLines={1}>
                      {item.type.charAt(0) + item.type.slice(1).toLowerCase()}
                    </Text>
                    {item.description ? (
                      <Text style={[styles.rowDescription, { color: secondary }]} numberOfLines={2}>
                        {item.description}
                      </Text>
                    ) : null}
                    <Text style={[styles.rowMeta, { color: secondary }]}>
                      {new Date(item.created_at).toLocaleString()} · Balance {item.balance_after}
                    </Text>
                  </View>
                </View>
              ))}
            </View>
          )}
        </ScrollView>
      )}
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
  state: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
  },
  errorText: {
    fontSize: typography.fontSize.bodySmall,
    textAlign: 'center',
    lineHeight: typography.lineHeight.bodySmall,
  },
  retryCta: {
    marginTop: spacing.lg,
    paddingHorizontal: spacing.xl,
    paddingVertical: 12,
    borderRadius: radius.full,
    ...shadows.accent,
  },
  retryCtaText: {
    color: colors.primary,
    fontWeight: '700',
    fontSize: typography.fontSize.body,
  },
  content: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xxxl,
  },
  balanceCard: {
    borderRadius: radius.xl,
    padding: spacing.xl,
    ...shadows.card,
  },
  balanceLabel: {
    color: colors.textOnDarkMuted,
    fontSize: typography.fontSize.caption,
    fontWeight: '700',
    letterSpacing: typography.letterSpacing.wider,
    textTransform: 'uppercase',
  },
  balanceNumber: {
    color: colors.accent,
    fontSize: 52,
    fontWeight: '800',
    marginTop: spacing.sm,
  },
  balanceDivider: {
    height: 1,
    backgroundColor: 'rgba(255,255,255,0.14)',
    marginVertical: spacing.md,
  },
  balanceStats: {
    flexDirection: 'row',
    gap: spacing.xl,
  },
  balanceStat: {
    alignItems: 'flex-start',
  },
  balanceStatValue: {
    color: colors.textOnDark,
    fontSize: typography.fontSize.heading,
    fontWeight: '800',
  },
  balanceStatLabel: {
    color: colors.textOnDarkMuted,
    fontSize: typography.fontSize.caption,
    marginTop: 2,
  },
  sectionLabel: {
    fontSize: typography.fontSize.caption,
    fontWeight: '700',
    letterSpacing: typography.letterSpacing.wider,
    textTransform: 'uppercase',
    marginTop: spacing.xl,
    marginBottom: spacing.md,
  },
  rows: {
    gap: spacing.sm,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.md,
  },
  amountBadge: {
    minWidth: 52,
    height: 40,
    borderRadius: radius.full,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.sm,
  },
  amountText: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '800',
  },
  rowInfo: {
    flex: 1,
  },
  rowTitle: {
    fontSize: typography.fontSize.body,
    fontWeight: '700',
  },
  rowDescription: {
    fontSize: typography.fontSize.bodySmall,
    marginTop: 2,
  },
  rowMeta: {
    fontSize: typography.fontSize.caption,
    marginTop: 4,
  },
  emptyCard: {
    alignItems: 'center',
    borderRadius: radius.xl,
    borderWidth: 1,
    padding: spacing.xxxl,
    paddingHorizontal: spacing.xl,
  },
  emptyEmoji: {
    fontSize: 34,
    color: colors.accent,
  },
  emptyTitle: {
    fontSize: typography.fontSize.heading,
    fontWeight: '700',
    textAlign: 'center',
    marginTop: spacing.md,
  },
  emptySub: {
    fontSize: typography.fontSize.bodySmall,
    textAlign: 'center',
    marginTop: spacing.sm,
    lineHeight: typography.lineHeight.bodySmall,
  },
});