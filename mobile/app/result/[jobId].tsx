import React, { useRef, useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  Image,
  PanResponder,
  TouchableOpacity,
  useColorScheme,
  ScrollView,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTryOn } from '../../src/context/TryOnContext';
import { colors, radius, spacing, typography, shadows } from '../../src/theme';
import { garmentsByGender, stylesForGarment } from '../../src/constants/garments';
import AppButton from '../../src/components/AppButton';
import { useHistoryItemQuery, useTryOnResultQuery } from '../../src/hooks/queries';
import { downloadImage, shareImage } from '../../src/utils/imageActions';

export default function ResultScreen() {
  const { jobId, historyId } = useLocalSearchParams<{ jobId: string; historyId?: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { draft, setDraft, reset } = useTryOn();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';

  const [slider, setSlider] = useState(0.5);
  const [showAfter, setShowAfter] = useState(true);
  const historyQuery = useHistoryItemQuery(typeof historyId === 'string' ? historyId : undefined);
  const resultQuery = useTryOnResultQuery(
    typeof jobId === 'string' ? jobId : undefined,
    !historyQuery.data?.result_url,
  );
  const hist = historyQuery.data;
  const [boxWidth, setBoxWidth] = useState(300);
  const [liveUrl, setLiveUrl] = useState<string | null>(null);
  const [imageAction, setImageAction] = useState<'download' | 'share' | null>(null);

  const bg = dark ? colors.darkBackground : colors.background;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const card = dark ? colors.darkSurface : colors.surface;
  const border = dark ? colors.darkBorder : colors.border;

  // A history route is authoritative. Never let the current try-on draft from
  // a previous screen override the selected history record.
  const historyResultUrl = typeof hist?.result_url === 'string' && hist.result_url.trim()
    ? hist.result_url
    : null;
  const draftResultUrl = typeof draft.resultUrl === 'string' && draft.resultUrl.trim()
    ? draft.resultUrl
    : null;
  useEffect(() => {
    if (resultQuery.data?.result_url) setLiveUrl(resultQuery.data.result_url);
  }, [resultQuery.data]);

  const resultUrl = historyId ? historyResultUrl || liveUrl : draftResultUrl || liveUrl;
  useEffect(() => {
    if (__DEV__) {
      console.log(`[HISTORY_DETAIL] routeId=${historyId ?? 'live'} jobId=${jobId ?? 'none'} resultUrl=${resultUrl ?? 'none'}`);
    }
  }, [historyId, jobId, resultUrl]);
  const personUrl = historyId ? hist?.person_image_url ?? null : draft.personImageUri;
  const fabricUrl = historyId ? hist?.fabric_image_url ?? null : draft.fabricImageUri;
  const garmentGender = (historyId ? hist?.gender : draft.gender) as 'MEN' | 'WOMEN' | 'KIDS' ?? 'WOMEN';
  const garmentId = historyId ? hist?.garment_type ?? '' : draft.garmentId ?? '';
  const styleId = historyId ? hist?.garment_style ?? '' : draft.styleId ?? '';
  const garment = garmentsByGender[garmentGender].find((g) => g.id === garmentId);
  const style = garmentId ? stylesForGarment(garmentId).find((s) => s.id === styleId) : undefined;

  const pan = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderMove: (_, gestureState) => {
        setSlider(
          Math.min(1, Math.max(0, gestureState.moveX / boxWidth))
        );
      },
    })
  ).current;

  const runImageAction = async (action: 'download' | 'share') => {
    if (imageAction) return;
    setImageAction(action);
    try {
      if (action === 'download') {
        await downloadImage(resultUrl);
        alert('Image saved to your gallery.');
      } else {
        await shareImage(resultUrl);
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : 'The image action could not be completed.');
    } finally {
      setImageAction(null);
    }
  };

  const onTryNewCloth = async () => {
    await setDraft({ fabricImageUri: null, fabricImageId: null });
    router.replace('/camera/fabric');
  };

  const onFreshLook = async () => {
    await reset();
    router.replace('/tryon');
  };

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={[styles.header, { paddingTop: insets.top + spacing.sm, paddingHorizontal: spacing.lg }]}>
          <Text style={[styles.title, { color: text }]}>Your Look Is Ready</Text>
          <TouchableOpacity
            onPress={() => router.replace('/(tabs)/history')}
            style={[styles.closeBtn, { backgroundColor: dark ? colors.darkSurfaceAlt : 'rgba(0,0,0,0.05)' }]}
          >
            <Text style={[styles.closeIcon, { color: secondary }]}>✕</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.compareWrap}>
          <View
            style={styles.compareBox}
            onLayout={(e) => setBoxWidth(e.nativeEvent.layout.width)}
            {...pan.panHandlers}
          >
            <Image
              source={{ uri: resultUrl ?? undefined }}
              style={styles.compareImg}
              resizeMode="cover"
              onLoadStart={() => __DEV__ && console.log(`[HISTORY_IMAGE] historyId=${historyId ?? 'live'} imageUrl=${resultUrl ?? 'none'} load=start`)}
              onLoad={() => __DEV__ && console.log(`[HISTORY_IMAGE] historyId=${historyId ?? 'live'} load=success`)}
              onError={(event) => __DEV__ && console.log(`[HISTORY_IMAGE] historyId=${historyId ?? 'live'} load=failed error=${event.nativeEvent.error}`)}
            />
            {personUrl ? (
              <View style={[styles.clipLayer, { width: boxWidth * slider }]}>
                <Image
                  source={{ uri: personUrl }}
                  style={[styles.compareImg, { width: boxWidth }]}
                  resizeMode="cover"
                />
              </View>
            ) : null}

            <View style={[styles.dividerLine, { left: boxWidth * slider - 1 }]} />
            <View style={[styles.handleWrap, { left: boxWidth * slider - 20 }]}>
              <View style={styles.handleBadge}>
                <Text style={styles.handleIcon}>⇄</Text>
              </View>
            </View>

            <View style={[styles.tagOriginal, { backgroundColor: 'rgba(13,11,26,0.85)' }]}>
              <Text style={styles.tagText}>ORIGINAL</Text>
            </View>
            <View style={[styles.tagTryOn, { backgroundColor: 'rgba(201,169,106,0.92)' }]}>
              <Text style={styles.tagText}>AI TRY-ON</Text>
            </View>

            <View style={styles.toggleWrap}>
              <TouchableOpacity
                style={[styles.toggleBtn, { backgroundColor: dark ? 'rgba(27,24,38,0.85)' : 'rgba(255,255,255,0.9)' }]}
                onPress={() => setShowAfter(!showAfter)}
              >
                <Text style={[styles.toggleText, { color: showAfter ? colors.accent : secondary }]}>
                  {showAfter ? 'AFTER' : 'BEFORE'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>

        <View style={styles.thumbStrip}>
          <Thumb label="YOUR PHOTO" uri={personUrl ?? null} dark={dark} />
          <Thumb label="SELECTED FABRIC" uri={fabricUrl ?? null} dark={dark} />
          <Thumb label="GENERATED LOOK" uri={resultUrl ?? null} dark={dark} accent />
        </View>

        <View style={[styles.metaCard, { backgroundColor: card, borderColor: border }]}>
          <MetaRow label="GARMENT" value={garment?.label ?? '—'} dark={dark} border={border} last={false} />
          <MetaRow label="STYLE" value={style?.label ?? '—'} dark={dark} border={border} last={false} />
          <MetaRow label="FABRIC" value="Selected by you" dark={dark} border={border} last />
        </View>

        <View style={styles.actionRow}>
          <ActionPill dark={dark} emoji="⇩" label={imageAction === 'download' ? 'Saving…' : 'Download'} onPress={() => runImageAction('download')} disabled={Boolean(imageAction)} />
          <ActionPill dark={dark} emoji="↗" label={imageAction === 'share' ? 'Sharing…' : 'Share'} onPress={() => runImageAction('share')} disabled={Boolean(imageAction)} />
          <ActionPill dark={dark} emoji="🔄" label="Regenerate" onPress={() => router.replace('/camera/person')} />
        </View>

        <View style={styles.ctaSection}>
          <AppButton
            title="Try Another Style"
            variant="accent"
            onPress={() => router.replace('/tryon/style')}
          />
          <TouchableOpacity onPress={onTryNewCloth} style={styles.secondaryCta}>
            <Text style={[styles.secondaryCtaText, { color: colors.accent }]}>
              Capture New Cloth
            </Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={onFreshLook} style={styles.secondaryCta}>
            <Text style={[styles.secondaryCtaText, { color: dark ? colors.darkTextSecondary : colors.textSecondary }]}>
              Start a Fresh Look (new photo + cloth)
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
}

function Thumb({
  label,
  uri,
  dark,
  accent,
}: {
  label: string;
  uri: string | null;
  dark: boolean;
  accent?: boolean;
}) {
  return (
    <View style={styles.thumb}>
      {uri ? (
        <Image source={{ uri }} style={styles.thumbImg} resizeMode="cover" />
      ) : (
        <View style={[styles.thumbPlaceholder, { backgroundColor: dark ? colors.darkSurfaceAlt : colors.surfaceAlt }]}>
          <Text style={styles.thumbPlaceholderText}>—</Text>
        </View>
      )}
      <Text
        style={[
          styles.thumbLabel,
          { color: accent ? colors.accent : dark ? colors.darkTextSecondary : colors.textSecondary },
        ]}
      >
        {label}
      </Text>
    </View>
  );
}

function MetaRow({
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
      <View style={styles.metaRow}>
        <Text style={styles.metaLabel}>{label}</Text>
        <Text style={[styles.metaValue, { color: dark ? colors.darkTextPrimary : colors.textPrimary }]}>
          {value}
        </Text>
      </View>
      {!last && <View style={[styles.metaDivider, { backgroundColor: border }]} />}
    </View>
  );
}

function ActionPill({
  dark,
  emoji,
  label,
  onPress,
  disabled = false,
}: {
  dark: boolean;
  emoji: string;
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <TouchableOpacity
      style={[
        styles.actionPill,
        { borderColor: dark ? colors.darkBorder : colors.border },
        disabled && styles.actionPillDisabled,
      ]}
      onPress={onPress}
      activeOpacity={0.7}
      disabled={disabled}
    >
      <Text style={styles.actionEmoji}>{emoji}</Text>
      <Text style={[styles.actionLabel, { color: dark ? colors.darkTextPrimary : colors.textPrimary }]}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: spacing.xxxl,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: typography.fontSize.heading,
    fontWeight: '800',
    letterSpacing: typography.letterSpacing.tight,
    flex: 1,
  },
  closeBtn: {
    width: 38,
    height: 38,
    borderRadius: radius.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
  closeIcon: {
    fontSize: 18,
    fontWeight: '700',
  },
  compareWrap: {
    paddingHorizontal: spacing.lg,
    marginTop: spacing.md,
  },
  compareBox: {
    height: 500,
    borderRadius: radius.xl,
    overflow: 'hidden',
    backgroundColor: '#E8E4DC',
    ...shadows.elevated,
  },
  compareImg: {
    width: '100%',
    height: '100%',
  },
  clipLayer: {
    position: 'absolute',
    top: 0,
    left: 0,
    height: '100%',
    overflow: 'hidden',
  },
  dividerLine: {
    position: 'absolute',
    top: 0,
    height: '100%',
    width: 2,
    backgroundColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 5,
  },
  handleWrap: {
    position: 'absolute',
    top: '50%',
    marginTop: -20,
    zIndex: 10,
  },
  handleBadge: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 6,
  },
  handleIcon: {
    fontSize: 18,
    color: colors.primary,
    fontWeight: '800',
  },
  tagOriginal: {
    position: 'absolute',
    bottom: 14,
    left: 14,
    borderRadius: radius.sm,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  tagTryOn: {
    position: 'absolute',
    bottom: 14,
    right: 14,
    borderRadius: radius.sm,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  tagText: {
    color: '#fff',
    fontSize: typography.fontSize.micro,
    fontWeight: '800',
    letterSpacing: 1.5,
  },
  toggleWrap: {
    position: 'absolute',
    top: 14,
    right: 14,
  },
  toggleBtn: {
    borderRadius: radius.full,
    paddingHorizontal: 14,
    paddingVertical: 7,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  toggleText: {
    fontSize: typography.fontSize.micro,
    fontWeight: '800',
    letterSpacing: 1,
  },
  metaCard: {
    marginHorizontal: spacing.lg,
    marginTop: spacing.lg,
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.md,
    ...shadows.soft,
  },
  actionPillDisabled: {
    opacity: 0.5,
  },
  thumbStrip: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    marginTop: spacing.lg,
  },
  thumb: {
    flex: 1,
    alignItems: 'center',
    gap: spacing.xs,
  },
  thumbImg: {
    width: '100%',
    aspectRatio: 3 / 4,
    borderRadius: radius.md,
    ...shadows.soft,
  },
  thumbPlaceholder: {
    width: '100%',
    aspectRatio: 3 / 4,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  thumbPlaceholderText: {
    fontSize: typography.fontSize.body,
    fontWeight: '700',
    color: colors.textMuted,
  },
  thumbLabel: {
    fontSize: typography.fontSize.micro,
    fontWeight: '800',
    letterSpacing: 0.5,
    textAlign: 'center',
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm + 2,
  },
  metaLabel: {
    fontSize: typography.fontSize.micro,
    fontWeight: '800',
    letterSpacing: 1.5,
    color: colors.textMuted,
  },
  metaValue: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '700',
  },
  metaDivider: {
    height: 1,
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.md,
    marginTop: spacing.lg,
    paddingHorizontal: spacing.lg,
  },
  actionPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs + 2,
    borderWidth: 1.5,
    borderRadius: radius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
    backgroundColor: 'transparent',
  },
  actionEmoji: {
    fontSize: 14,
  },
  actionLabel: {
    fontSize: typography.fontSize.caption,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  ctaSection: {
    paddingHorizontal: spacing.lg,
    marginTop: spacing.xl,
    gap: spacing.sm,
    alignItems: 'center',
  },
  secondaryCta: {
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  secondaryCtaText: {
    fontSize: typography.fontSize.body,
    fontWeight: '700',
  },
});
