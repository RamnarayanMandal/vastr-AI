import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  Image,
  TouchableOpacity,
  useColorScheme,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useHistoryQuery } from '../../src/hooks/queries';
import { parseApiError } from '../../src/api/errors';
import { colors, radius, spacing, typography, shadows } from '../../src/theme';
import BottomNav from '../../src/components/BottomNav';

const filters = ['All', 'Men', 'Women', 'Kids', 'Saved'];

export default function HistoryScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  const [filter, setFilter] = useState('All');
  const historyQuery = useHistoryQuery();
  const history = historyQuery.data ?? [];

  const bg = dark ? colors.darkBackground : colors.background;
  const surface = dark ? colors.darkSurface : colors.surface;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const border = dark ? colors.darkBorder : colors.border;

  const filtered = filter === 'All' ? history : history.filter((h) => h.gender === filter.toUpperCase());

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.lg }]}>
        <Text style={[styles.title, { color: text }]}>Your Try-Ons</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.filtersContainer}
        >
          {filters.map((f) => {
            const active = filter === f;
            return (
              <TouchableOpacity
                key={f}
                style={[
                  styles.chip,
                  {
                    backgroundColor: active ? colors.primary : surface,
                    borderColor: active ? colors.primary : border,
                  },
                ]}
                activeOpacity={0.7}
                onPress={() => setFilter(f)}
              >
                <Text
                  style={[
                    styles.chipText,
                    { color: active ? colors.textOnDark : secondary },
                  ]}
                >
                  {f}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      <ScrollView
        contentContainerStyle={styles.gridContent}
        showsVerticalScrollIndicator={false}
      >
        {historyQuery.isLoading ? <Text style={{ color: secondary }}>Loading history…</Text> : historyQuery.isError ? <View style={styles.emptyState}><Text style={[styles.emptyTitle, { color: colors.danger }]}>{parseApiError(historyQuery.error).message}</Text><TouchableOpacity style={styles.emptyCta} onPress={() => historyQuery.refetch()}><Text style={styles.emptyCtaText}>Retry</Text></TouchableOpacity></View> : filtered.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyEmoji}>👗</Text>
            <Text style={[styles.emptyTitle, { color: text }]}>No looks yet</Text>
            <Text style={[styles.emptySub, { color: secondary }]}>
              Create your first look and it will appear here.
            </Text>
            <TouchableOpacity
              style={styles.emptyCta}
              activeOpacity={0.85}
              onPress={() => router.push('/tryon')}
            >
              <Text style={styles.emptyCtaText}>Create Your First Look</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.grid}>
            {filtered.map((item) => (
              <TouchableOpacity
                key={item.id}
                style={[styles.card, { backgroundColor: surface, borderColor: border }]}
                activeOpacity={0.75}
                onPress={() => {
                  if (__DEV__) console.log(`[HISTORY_CLICK] historyId=${item.id} jobId=${item.job_id}`);
                  router.push(`/result/${item.job_id}?historyId=${item.id}`);
                }}
              >
                <Image source={{ uri: item.result_url }} style={styles.cardImg} />
                <View style={styles.cardInfo}>
                  <Text style={[styles.cardTitle, { color: text }]} numberOfLines={1}>
                    {item.garment_type}
                  </Text>
                  <Text style={[styles.cardMeta, { color: secondary }]} numberOfLines={1}>
                    {item.garment_style} · {new Date(item.created_at).toLocaleDateString()}
                  </Text>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}
        <View style={{ height: spacing.xl }} />
      </ScrollView>
      <BottomNav />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  header: { paddingHorizontal: spacing.lg },
  title: {
    fontSize: typography.fontSize.title,
    fontWeight: '800',
    letterSpacing: typography.letterSpacing.tight,
  },
  filtersContainer: {
    gap: spacing.sm,
    paddingVertical: spacing.md,
    paddingRight: spacing.lg,
  },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.full,
    borderWidth: 1,
  },
  chipText: {
    fontWeight: '600',
    fontSize: typography.fontSize.bodySmall,
  },
  gridContent: {
    paddingHorizontal: spacing.lg,
    paddingBottom: 40,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  card: {
    width: '47%',
    borderRadius: radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    ...shadows.card,
  },
  cardImg: {
    width: '100%',
    aspectRatio: 0.78,
  },
  cardInfo: { padding: spacing.sm },
  cardTitle: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '700',
  },
  cardMeta: {
    fontSize: typography.fontSize.caption,
    marginTop: 3,
  },
  emptyState: {
    alignItems: 'center',
    marginTop: 80,
    paddingHorizontal: spacing.xl,
  },
  emptyEmoji: { fontSize: 52 },
  emptyTitle: {
    fontSize: typography.fontSize.heading,
    fontWeight: '700',
    marginTop: spacing.md,
    letterSpacing: typography.letterSpacing.tight,
  },
  emptySub: {
    fontSize: typography.fontSize.bodySmall,
    textAlign: 'center',
    marginTop: spacing.sm,
    lineHeight: typography.lineHeight.bodySmall,
  },
  emptyCta: {
    marginTop: spacing.lg,
    backgroundColor: colors.accent,
    paddingHorizontal: spacing.xl,
    paddingVertical: 14,
    borderRadius: radius.full,
    ...shadows.accent,
  },
  emptyCtaText: {
    color: colors.primary,
    fontWeight: '700',
    fontSize: typography.fontSize.body,
  },
});
