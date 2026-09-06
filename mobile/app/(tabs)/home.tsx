import React, { useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  useColorScheme,
  Image,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '../../src/context/AuthContext';
import { useTryOn } from '../../src/context/TryOnContext';
import { colors, radius, spacing, typography, shadows } from '../../src/theme';
import { genders } from '../../src/constants/garments';
import { useHistoryQuery } from '../../src/hooks/queries';
import BottomNav from '../../src/components/BottomNav';

const categories = [
  { label: 'Sarees', emoji: '🥻' },
  { label: 'Kurtas', emoji: '👔' },
  { label: 'Pants', emoji: '👖' },
  { label: 'Dresses', emoji: '👗' },
];

export default function HomeScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const { setDraft } = useTryOn();
  const insets = useSafeAreaInsets();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  const historyQuery = useHistoryQuery();
  const history = historyQuery.data ?? [];

  const bg = dark ? colors.darkBackground : colors.background;
  const surface = dark ? colors.darkSurface : colors.surface;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const border = dark ? colors.darkBorder : colors.border;
  const surfaceAlt = dark ? colors.darkSurfaceAlt : colors.surfaceAlt;

  const selectGender = useCallback(
    (g: (typeof genders)[number]) => {
      setDraft({ gender: g.id });
      router.push('/tryon/garment');
    },
    [router, setDraft]
  );

  const firstName = (user?.full_name ?? 'there').split(' ')[0];
  const initials = (user?.full_name ?? 'V').split(' ').map((w: string) => w[0]).join('').slice(0, 2).toUpperCase();

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={[styles.topBar, { paddingTop: insets.top + spacing.md }]}>
          <View>
            <Text style={[styles.greeting, { color: secondary }]}>Hi, {firstName}</Text>
            <Text style={[styles.brand, { color: text }]}>VastrAI</Text>
          </View>
          <View style={styles.topActions}>
            <TouchableOpacity
              style={[styles.bellBtn, { backgroundColor: surfaceAlt, borderColor: border }]}
              onPress={() => alert('No new notifications.')}
            >
              <Text style={styles.bellIcon}>🔔</Text>
            </TouchableOpacity>
            <View style={styles.avatarCircle}>
              <Text style={styles.avatarInitials}>{initials}</Text>
            </View>
          </View>
        </View>

        <View style={[styles.hero, { backgroundColor: dark ? colors.primaryLight : colors.primary }]}>
          <View style={styles.heroContent}>
            <Text style={styles.heroTitle}>Try Before{'\n'}You Stitch</Text>
            <Text style={styles.heroSub}>See how your fabric or garment could look on you.</Text>
            <TouchableOpacity
              style={styles.heroCta}
              activeOpacity={0.85}
              onPress={() => router.push('/tryon')}
            >
              <Text style={styles.heroCtaText}>Start Virtual Try-On ✨</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.sparkleCluster}>
            <Text style={[styles.sparkle, { top: 8, right: 12 }]}>✦</Text>
            <Text style={[styles.sparkle, { top: 28, right: 36, fontSize: 14, opacity: 0.35 }]}>✧</Text>
            <Text style={[styles.sparkle, { bottom: 14, right: 8, fontSize: 18, opacity: 0.25 }]}>✦</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: text }]}>Who are you shopping for?</Text>
          <View style={styles.genderRow}>
            {genders.map((g) => (
              <TouchableOpacity
                key={g.id}
                style={[styles.genderCard, { backgroundColor: surface, borderColor: border }]}
                activeOpacity={0.7}
                onPress={() => selectGender(g)}
              >
                <View style={styles.genderEmojiCircle}>
                  <Text style={styles.genderEmoji}>{g.emoji}</Text>
                </View>
                <Text style={[styles.genderLabel, { color: text }]}>{g.label}</Text>
                <Text style={[styles.genderTagline, { color: secondary }]}>{g.tagline}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: text }]}>Popular Categories</Text>
          <View style={styles.categoriesGrid}>
            {categories.map((c) => (
              <TouchableOpacity
                key={c.label}
                style={[styles.categoryCard, { backgroundColor: surface, borderColor: border }]}
                activeOpacity={0.7}
                onPress={() => router.push('/tryon/garment')}
              >
                <Text style={styles.categoryEmoji}>{c.emoji}</Text>
                <Text style={[styles.categoryLabel, { color: text }]}>{c.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.section}>
          <View style={styles.sectionHeaderRow}>
            <Text style={[styles.sectionTitle, { color: text }]}>Recent Try-Ons</Text>
            <TouchableOpacity onPress={() => router.push('/history')}>
              <Text style={styles.viewAllLink}>View all</Text>
            </TouchableOpacity>
          </View>
          {history.length === 0 ? (
            <TouchableOpacity
              style={[styles.emptyCard, { backgroundColor: surface, borderColor: border }]}
              activeOpacity={0.7}
              onPress={() => router.push('/tryon')}
            >
              <Text style={styles.emptyEmoji}>✨</Text>
              <Text style={[styles.emptyTitle, { color: text }]}>No looks yet</Text>
              <Text style={[styles.emptySub, { color: secondary }]}>
                Create your first virtual try-on
              </Text>
            </TouchableOpacity>
          ) : (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.historyScroll}
            >
              {history.slice(0, 6).map((item) => (
                <TouchableOpacity
                  key={item.id}
                  style={[styles.historyCard, { backgroundColor: surface }]}
                  activeOpacity={0.75}
                  onPress={() => router.push(`/result/${item.job_id}?historyId=${item.id}`)}
                >
                  <Image source={{ uri: item.result_url }} style={styles.historyImg} />
                  <Text style={[styles.historyLabel, { color: text }]} numberOfLines={1}>
                    {item.garment_type}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          )}
        </View>

        <View style={{ height: spacing.xl }} />
      </ScrollView>
      <BottomNav />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  scrollContent: { paddingBottom: 40 },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
  },
  greeting: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '500',
    letterSpacing: typography.letterSpacing.wide,
  },
  brand: {
    fontSize: typography.fontSize.title,
    fontWeight: '800',
    marginTop: 2,
    letterSpacing: typography.letterSpacing.tight,
  },
  topActions: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  bellBtn: {
    width: 42,
    height: 42,
    borderRadius: radius.full,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bellIcon: { fontSize: 18 },
  avatarCircle: {
    width: 42,
    height: 42,
    borderRadius: radius.full,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    ...shadows.soft,
  },
  avatarInitials: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.primary,
    letterSpacing: 0.5,
  },
  hero: {
    marginHorizontal: spacing.lg,
    marginTop: spacing.lg,
    borderRadius: radius.xl,
    padding: spacing.xl,
    paddingTop: spacing.xl + 4,
    paddingBottom: spacing.xl + 4,
    overflow: 'hidden',
    minHeight: 200,
  },
  heroContent: { maxWidth: 280 },
  heroTitle: {
    fontSize: 30,
    fontWeight: '800',
    color: colors.textOnDark,
    lineHeight: 38,
    letterSpacing: typography.letterSpacing.tight,
  },
  heroSub: {
    fontSize: typography.fontSize.bodySmall,
    color: colors.textOnDarkMuted,
    marginTop: spacing.sm,
    lineHeight: typography.lineHeight.bodySmall,
  },
  heroCta: {
    marginTop: spacing.lg,
    backgroundColor: colors.accent,
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.lg,
    paddingVertical: 14,
    borderRadius: radius.full,
    ...shadows.accent,
  },
  heroCtaText: {
    color: colors.primary,
    fontWeight: '700',
    fontSize: typography.fontSize.body,
  },
  sparkleCluster: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    width: 80,
  },
  sparkle: {
    position: 'absolute',
    color: colors.accent,
    fontSize: 20,
    opacity: 0.45,
  },
  section: {
    paddingHorizontal: spacing.lg,
    marginTop: spacing.xl + 4,
  },
  sectionTitle: {
    fontSize: typography.fontSize.heading,
    fontWeight: '700',
    letterSpacing: typography.letterSpacing.tight,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  viewAllLink: {
    color: colors.accentDark,
    fontWeight: '700',
    fontSize: typography.fontSize.bodySmall,
  },
  genderRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.md,
  },
  genderCard: {
    flex: 1,
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.md,
    alignItems: 'center',
    ...shadows.soft,
  },
  genderEmojiCircle: {
    width: 54,
    height: 54,
    borderRadius: radius.full,
    backgroundColor: colors.accentSoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  genderEmoji: { fontSize: 26 },
  genderLabel: {
    fontSize: typography.fontSize.body,
    fontWeight: '700',
    marginTop: spacing.sm,
  },
  genderTagline: {
    fontSize: typography.fontSize.caption,
    marginTop: 2,
    textAlign: 'center',
  },
  categoriesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginTop: spacing.md,
  },
  categoryCard: {
    width: '47%',
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    ...shadows.soft,
  },
  categoryEmoji: { fontSize: 28 },
  categoryLabel: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '700',
  },
  historyScroll: { gap: spacing.md, paddingTop: spacing.md },
  historyCard: {
    width: 150,
    borderRadius: radius.lg,
    overflow: 'hidden',
    ...shadows.card,
  },
  historyImg: { width: 150, height: 180 },
  historyLabel: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '700',
    padding: spacing.sm,
    paddingBottom: spacing.md,
  },
  emptyCard: {
    marginTop: spacing.md,
    alignItems: 'center',
    borderRadius: radius.lg,
    borderWidth: 1,
    borderStyle: 'dashed',
    paddingVertical: spacing.xl + 4,
    paddingHorizontal: spacing.xl,
  },
  emptyEmoji: { fontSize: 32 },
  emptyTitle: {
    fontSize: typography.fontSize.body,
    fontWeight: '700',
    marginTop: spacing.sm,
  },
  emptySub: {
    fontSize: typography.fontSize.bodySmall,
    marginTop: 4,
  },
});
