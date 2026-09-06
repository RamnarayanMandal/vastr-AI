import React, { useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  useColorScheme,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTryOn } from '../../src/context/TryOnContext';
import { colors, radius, spacing, typography, shadows } from '../../src/theme';
import { garmentsByGender } from '../../src/constants/garments';

export default function GarmentScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { draft, setDraft } = useTryOn();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';

  const bg = dark ? colors.darkBackground : colors.background;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const card = dark ? colors.darkSurface : '#fff';
  const border = dark ? colors.darkBorder : colors.border;

  const garments = garmentsByGender[draft.gender];

  const selected = useCallback(
    (g: (typeof garments)[number]) => {
      setDraft({ garmentId: g.id });
      router.push('/tryon/upload');
    },
    [router, setDraft]
  );

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <View style={{ paddingTop: insets.top + spacing.md }}>
        <TouchableOpacity onPress={() => router.back()} style={styles.back}>
          <Text style={{ color: text, fontSize: 24 }}>‹</Text>
        </TouchableOpacity>
        <Text style={[styles.title, { color: text }]}>What do you want to make?</Text>
        <Text style={[styles.sub, { color: secondary }]}>Choose the garment for {draft.gender.toLowerCase()}.</Text>
      </View>

      <ScrollView contentContainerStyle={styles.grid}>
        {garments.map((g) => (
          <TouchableOpacity key={g.id} style={[styles.card, { backgroundColor: card, borderColor: border }]} onPress={() => selected(g)}>
            <View style={[styles.emojiWrap, { backgroundColor: colors.accentSoft }]}>
              <Text style={styles.garmentEmoji}>{g.emoji}</Text>
            </View>
            <Text style={[styles.cardTitle, { color: text }]}>{g.label}</Text>
            <Text style={[styles.cardTagline, { color: secondary }]}>{g.tagline}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  back: { alignSelf: 'flex-start', marginHorizontal: spacing.lg },
  title: { fontSize: typography.fontSize.title, fontWeight: '800', marginHorizontal: spacing.lg, marginTop: spacing.sm },
  sub: { fontSize: typography.fontSize.bodySmall, marginHorizontal: spacing.lg, marginTop: 4, marginBottom: spacing.md },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: spacing.md, paddingHorizontal: spacing.lg, paddingBottom: 40 },
  card: {
    width: '47%', borderRadius: radius.lg, borderWidth: 1, padding: spacing.md, alignItems: 'center',
    ...shadows.soft,
  },
  emojiWrap: { width: 64, height: 64, borderRadius: radius.full, alignItems: 'center', justifyContent: 'center' },
  garmentEmoji: { fontSize: 28 },
  cardTitle: { fontSize: typography.fontSize.body, fontWeight: '700', marginTop: spacing.sm },
  cardTagline: { fontSize: typography.fontSize.caption, marginTop: 2, textAlign: 'center' },
});