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
import { useTryOn } from '../src/context/TryOnContext';
import { colors, radius, spacing, typography, shadows } from '../src/theme';
import AppButton from '../src/components/AppButton';
import { garmentsByGender, stylesForGarment } from '../src/constants/garments';

export default function ReviewScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { draft, generate } = useTryOn();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';

  const [generating, setGenerating] = useState(false);

  const bg = dark ? colors.darkBackground : colors.background;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const card = dark ? colors.darkSurface : colors.surface;
  const surfaceAlt = dark ? colors.darkSurfaceAlt : colors.surfaceAlt;
  const border = dark ? colors.darkBorder : colors.border;

  const garment = garmentsByGender[draft.gender].find((g) => g.id === draft.garmentId);
  const style = draft.garmentId
    ? stylesForGarment(draft.garmentId).find((s) => s.id === draft.styleId)
    : undefined;

  const complete =
    !!draft.personImageId &&
    !!draft.fabricImageId &&
    !!draft.garmentId &&
    !!draft.styleId;

  // Display the local URI captured on-device (reliably renders as file://).
  // The server-uploaded URL can be a relative /local_uploads path, which
  // react-native <Image> cannot load, so it must NOT be used for display here.
  const personImgSrc = draft.personImageUri;
  const fabricImgSrc = draft.fabricImageUri;

  const onGenerate = async () => {
    setGenerating(true);
    try {
      const jobId = await generate();
      router.replace(`/processing/${jobId}`);
    } catch (e: any) {
      const details = [
        e.message,
        e.status ? `HTTP ${e.status}` : null,
        e.code ? `Code: ${e.code}` : null,
        e.jobId ? `Job: ${e.jobId}` : null,
      ].filter(Boolean).join('\n');
      alert(details || 'Generate request failed.');
      setGenerating(false);
    }
  };

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <View
        style={[
          styles.header,
          { paddingTop: insets.top + spacing.sm },
        ]}
      >
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Text style={[styles.backArrow, { color: text }]}>‹</Text>
        </TouchableOpacity>
        <View style={styles.headerTextWrap}>
          <Text style={[styles.title, { color: text }]}>Review Your Look</Text>
          <Text style={[styles.subtitle, { color: secondary }]}>
            Check both images before generating.
          </Text>
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.imageRow}>
          <ImageCard
            label="YOUR PHOTO"
            uri={personImgSrc}
            placeholder="Photo required"
            dark={dark}
            card={card}
            surfaceAlt={surfaceAlt}
            border={border}
          />
          <View style={styles.plusWrap}>
            <View style={styles.plusCircle}>
              <Text style={styles.plusSign}>+</Text>
            </View>
          </View>
          <ImageCard
            label="SELECTED FABRIC"
            uri={fabricImgSrc}
            placeholder="Cloth required"
            dark={dark}
            card={card}
            surfaceAlt={surfaceAlt}
            border={border}
          />
        </View>

        <View style={[styles.summaryCard, { backgroundColor: card, borderColor: border }]}>
          <SummaryRow label="WHO" value={draft.gender.charAt(0) + draft.gender.slice(1).toLowerCase()} dark={dark} border={border} last={false} />
          <SummaryRow label="GARMENT" value={garment?.label ?? 'Not selected'} dark={dark} border={border} last={false} />
          <SummaryRow label="STYLE" value={style?.label ?? 'Not selected'} dark={dark} border={border} last />
        </View>

        <View style={[styles.checklistCard, { backgroundColor: card, borderColor: border }]}>
          <Text style={[styles.checklistTitle, { color: text }]}>CHECKLIST</Text>
          <View style={[styles.checkDivider, { backgroundColor: border }]} />
          <CheckItem ok={!!draft.personImageId} label="Your Photo added" dark={dark} />
          <CheckItem ok={!!draft.fabricImageId} label="Cloth Selected" dark={dark} />
          <CheckItem ok={!!draft.garmentId} label="Garment Selected" dark={dark} />
          <CheckItem ok={!!draft.styleId} label="Style Selected" dark={dark} />
        </View>

        {!complete && (
          <View style={[styles.warningBox, { borderColor: colors.danger }]}>
            <View style={styles.warningHeader}>
              <Text style={styles.warningIcon}>⚠</Text>
              <Text style={[styles.warningTitle, { color: colors.danger }]}>Missing Items</Text>
            </View>
            <View style={styles.warningList}>
              {!draft.personImageId && (
                <Text style={[styles.warningItem, { color: colors.danger }]}>✕ Customer photo is required</Text>
              )}
              {!draft.fabricImageId && (
                <Text style={[styles.warningItem, { color: colors.danger }]}>✕ Cloth image is required</Text>
              )}
              {!draft.garmentId && (
                <Text style={[styles.warningItem, { color: colors.danger }]}>✕ Please select a garment</Text>
              )}
              {!draft.styleId && (
                <Text style={[styles.warningItem, { color: colors.danger }]}>✕ Please select a style</Text>
              )}
            </View>
          </View>
        )}
      </ScrollView>

      <View
        style={[
          styles.footer,
          { paddingBottom: insets.bottom + spacing.md, borderTopColor: border },
        ]}
      >
        <AppButton
          title="✨ Generate My Look"
          variant="accent"
          onPress={onGenerate}
          disabled={!complete || generating}
          loading={generating}
        />
        <TouchableOpacity onPress={() => router.back()} style={styles.editLink}>
          <Text style={[styles.editText, { color: colors.accent }]}>Edit</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

function ImageCard({
  label,
  uri,
  placeholder,
  dark,
  card,
  surfaceAlt,
  border,
}: {
  label: string;
  uri: string | null;
  placeholder: string;
  dark: boolean;
  card: string;
  surfaceAlt: string;
  border: string;
}) {
  return (
    <View style={[styles.imageCard, { backgroundColor: card, borderColor: border }]}>
      <Text style={[styles.imageCardLabel, { color: colors.textMuted }]}>{label}</Text>
      {uri ? (
        <Image source={{ uri }} style={styles.imageCardImg} />
      ) : (
        <View style={[styles.imageCardPlaceholder, { backgroundColor: surfaceAlt }]}>
          <View style={styles.placeholderIconWrap}>
            <Text style={[styles.placeholderIcon, { color: colors.textMuted }]}>📷</Text>
          </View>
          <Text style={[styles.placeholderText, { color: colors.danger }]}>{placeholder}</Text>
        </View>
      )}
    </View>
  );
}

function SummaryRow({
  label,
  value,
  dark,
  border,
  last,
}: {
  label: string;
  value: string;
  dark: boolean;
  border: string;
  last: boolean;
}) {
  return (
    <View>
      <View style={styles.summaryRow}>
        <Text style={styles.summaryLabel}>{label}</Text>
        <Text style={[styles.summaryValue, { color: dark ? colors.darkTextPrimary : colors.textPrimary }]}>
          {value}
        </Text>
      </View>
      {!last && <View style={[styles.summaryDivider, { backgroundColor: border }]} />}
    </View>
  );
}

function CheckItem({ ok, label, dark }: { ok: boolean; label: string; dark: boolean }) {
  return (
    <View style={styles.checkItem}>
      <View
        style={[
          styles.checkCircle,
          {
            backgroundColor: ok ? colors.success : dark ? colors.darkSurfaceAlt : colors.surfaceAlt,
            borderColor: ok ? colors.success : dark ? colors.darkBorder : colors.border,
          },
        ]}
      >
        <Text
          style={[
            styles.checkIcon,
            { color: ok ? '#fff' : colors.textMuted },
          ]}
        >
          {ok ? '✓' : '✕'}
        </Text>
      </View>
      <Text
        style={[
          styles.checkLabel,
          { color: ok ? colors.success : colors.textMuted },
        ]}
      >
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  header: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.sm,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: radius.full,
    backgroundColor: 'rgba(0,0,0,0.04)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  backArrow: {
    fontSize: 28,
    fontWeight: '300',
    marginTop: -2,
  },
  headerTextWrap: {
    marginTop: spacing.md,
  },
  title: {
    fontSize: typography.fontSize.heading,
    fontWeight: '800',
    letterSpacing: typography.letterSpacing.tight,
  },
  subtitle: {
    fontSize: typography.fontSize.bodySmall,
    marginTop: spacing.xs,
  },
  content: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xl,
    gap: spacing.md,
  },
  imageRow: {
    flexDirection: 'row',
    alignItems: 'stretch',
    gap: spacing.xs,
  },
  imageCard: {
    flex: 1,
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.sm,
    overflow: 'hidden',
    ...shadows.soft,
  },
  imageCardLabel: {
    fontSize: typography.fontSize.micro,
    fontWeight: '800',
    letterSpacing: 1.5,
    marginBottom: spacing.xs,
    marginLeft: 2,
  },
  imageCardImg: {
    width: '100%',
    aspectRatio: 0.75,
    borderRadius: radius.md,
  },
  imageCardPlaceholder: {
    width: '100%',
    aspectRatio: 0.75,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(0,0,0,0.05)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  placeholderIcon: {
    fontSize: 20,
  },
  placeholderText: {
    fontSize: typography.fontSize.caption,
    fontWeight: '700',
    textAlign: 'center',
  },
  plusWrap: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 30,
  },
  plusCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    ...shadows.accent,
  },
  plusSign: {
    fontSize: 20,
    fontWeight: '800',
    color: colors.primary,
    marginTop: -1,
  },
  summaryCard: {
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.md,
    ...shadows.soft,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm + 2,
  },
  summaryLabel: {
    fontSize: typography.fontSize.micro,
    fontWeight: '800',
    letterSpacing: 1.5,
    color: colors.textMuted,
  },
  summaryValue: {
    fontSize: typography.fontSize.body,
    fontWeight: '700',
  },
  summaryDivider: {
    height: 1,
  },
  checklistCard: {
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.md,
    ...shadows.soft,
  },
  checklistTitle: {
    fontSize: typography.fontSize.micro,
    fontWeight: '800',
    letterSpacing: 1.5,
    marginBottom: spacing.sm,
  },
  checkDivider: {
    height: 1,
    marginBottom: spacing.sm,
  },
  checkItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.xs + 2,
  },
  checkCircle: {
    width: 26,
    height: 26,
    borderRadius: 13,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkIcon: {
    fontSize: 12,
    fontWeight: '800',
  },
  checkLabel: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '600',
  },
  warningBox: {
    borderRadius: radius.lg,
    backgroundColor: colors.dangerSoft,
    borderWidth: 1,
    padding: spacing.md,
  },
  warningHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  warningIcon: {
    fontSize: 16,
  },
  warningTitle: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '800',
  },
  warningList: {
    gap: spacing.xs,
  },
  warningItem: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '600',
    lineHeight: 20,
  },
  footer: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    borderTopWidth: 1,
    gap: spacing.xs,
  },
  editLink: {
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  editText: {
    fontSize: typography.fontSize.body,
    fontWeight: '700',
  },
});
