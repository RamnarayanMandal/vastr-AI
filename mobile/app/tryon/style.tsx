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
import { stylesForGarment } from '../../src/constants/garments';
import AppButton from '../../src/components/AppButton';

export default function StyleScreen() {
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

  const styleOptions = draft.garmentId ? stylesForGarment(draft.garmentId) : [];
  const garmentLabel = draft.garmentId ? draft.garmentId.replace('_', ' ').toUpperCase() : '';

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <View style={{ paddingTop: insets.top + spacing.md }}>
        <TouchableOpacity onPress={() => router.back()} style={styles.back}>
          <Text style={{ color: text, fontSize: 24 }}>‹</Text>
        </TouchableOpacity>
        <Text style={[styles.title, { color: text }]}>Choose your style</Text>
        <Text style={[styles.sub, { color: secondary }]}>{garmentLabel} — how do you like it?</Text>
      </View>

      <ScrollView contentContainerStyle={styles.grid}>
        {styleOptions.map((s) => {
          const active = draft.styleId === s.id;
          return (
            <TouchableOpacity key={s.id} style={[styles.card, { backgroundColor: active ? colors.primary : card, borderColor: active ? colors.primary : border }]} onPress={() => setDraft({ styleId: s.id })}>
              <Text style={styles.styleEmoji}>{s.emoji}</Text>
              <Text style={[styles.cardTitle, { color: active ? colors.textOnDark : text }]}>{s.label}</Text>
              {active && <Text style={styles.check}>✓</Text>}
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      <View style={[styles.footer, { paddingBottom: insets.bottom + spacing.md }]}>
        <AppButton
          title="Continue"
          variant={draft.styleId ? 'accent' : 'ghost'}
          disabled={!draft.styleId}
          onPress={() => router.push('/review')}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  back: { alignSelf: 'flex-start', marginHorizontal: spacing.lg },
  title: { fontSize: typography.fontSize.title, fontWeight: '800', marginHorizontal: spacing.lg, marginTop: spacing.sm },
  sub: { fontSize: typography.fontSize.bodySmall, marginHorizontal: spacing.lg, marginTop: 4, marginBottom: spacing.md },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: spacing.md, paddingHorizontal: spacing.lg, paddingBottom: 20 },
  card: {
    width: '47%', borderRadius: radius.lg, borderWidth: 2, padding: spacing.lg, alignItems: 'center',
    ...shadows.soft,
  },
  styleEmoji: { fontSize: 32 },
  cardTitle: { fontSize: typography.fontSize.body, fontWeight: '700', marginTop: spacing.sm, textAlign: 'center' },
  check: { position: 'absolute', top: 8, right: 12, color: colors.accent, fontSize: 18, fontWeight: '800' },
  footer: { paddingHorizontal: spacing.lg, paddingTop: spacing.sm },
});