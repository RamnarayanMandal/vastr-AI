import React, { useEffect, useRef, useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  Image,
  Animated,
  useColorScheme,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTryOn } from '../../src/context/TryOnContext';
import { colors, radius, spacing, typography, shadows } from '../../src/theme';
import { useTryOnStatusQuery } from '../../src/hooks/queries';
import { parseApiError } from '../../src/api/errors';
import ProgressBar from '../../src/components/ProgressBar';

const STAGES = [
  { key: 'analyzing_photo', label: 'Analyzing photo' },
  { key: 'analyzing_fabric', label: 'Analyzing cloth' },
  { key: 'creating_look', label: 'Applying fabric' },
  { key: 'creating_outfit', label: 'Creating outfit' },
  { key: 'finalizing', label: 'Finalizing' },
];

export default function ProcessingScreen() {
  const { jobId } = useLocalSearchParams<{ jobId: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { draft, setDraft } = useTryOn();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';

  const [stageIdx, setStageIdx] = useState(0);
  const pulse = useRef(new Animated.Value(0)).current;
  const statusQuery = useTryOnStatusQuery(typeof jobId === 'string' ? jobId : undefined);
  const job = statusQuery.data;
  const jobStatus = job?.status ?? 'QUEUED';

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 1400,
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: 1400,
          useNativeDriver: true,
        }),
      ])
    ).start();

  }, []);

  useEffect(() => {
    if (!job) return;
    setStageIdx(job.status === 'QUEUED' ? 0 : job.status === 'PROCESSING' ? 2 : job.status === 'COMPLETED' ? STAGES.length - 1 : 0);
    if (job.status === 'COMPLETED' && job.result_url && typeof jobId === 'string') {
      setDraft({ jobId, status: 'COMPLETED', resultUrl: job.result_url, error: null });
      router.replace(`/result/${jobId}`);
    } else if (job.status === 'FAILED') {
      setDraft({ error: job.error_message || 'Your look could not be created.' });
      router.replace(`/processing-error/${jobId}`);
    }
  }, [job, jobId, router, setDraft]);

  useEffect(() => {
    if (statusQuery.error) setDraft({ error: parseApiError(statusQuery.error).message });
  }, [statusQuery.error, setDraft]);

  const bg = dark ? colors.darkBackground : colors.background;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const card = dark ? colors.darkSurface : '#fff';
  const cardBorder = dark ? colors.darkBorder : colors.borderLight;

  // Indeterminate mode: we do NOT show a (fake) numeric percentage because the
  // backend only reports coarse status. The bar sweeps to indicate activity.
  const progressLabel =
    jobStatus === 'COMPLETED'
      ? 'Finalized'
      : stageIdx === STAGES.length - 1
      ? 'Finalizing'
      : 'Generating your look';
  const done = jobStatus === 'COMPLETED';

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <View style={{ paddingTop: insets.top + spacing.xl }} />

      <Text style={[styles.title, { color: text }]}>Creating your look…</Text>
      <Text style={[styles.sub, { color: secondary }]}>
        AI is fitting your selected garment to your photo.
      </Text>

      <View style={styles.visual}>
        <View style={[styles.imgCard, { backgroundColor: card, borderColor: cardBorder }]}>
          {draft.personImageUri && (
            <Image
              source={{ uri: draft.personImageUri }}
              style={styles.img}
            />
          )}
        </View>

        <Animated.View
          style={[
            styles.plusBadge,
            {
              opacity: pulse.interpolate({
                inputRange: [0, 1],
                outputRange: [0.5, 1],
              }),
              transform: [
                {
                  scale: pulse.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.88, 1],
                  }),
                },
              ],
            },
          ]}
        >
          <Text style={styles.plusText}>+</Text>
        </Animated.View>

        <View style={[styles.imgCard, { backgroundColor: card, borderColor: cardBorder }]}>
          {draft.fabricImageUri && (
            <Image
              source={{ uri: draft.fabricImageUri }}
              style={styles.img}
            />
          )}
        </View>
      </View>

      <View style={styles.progressWrap}>
        <ProgressBar percent={100} label={progressLabel} dark={!!dark} indeterminate={!done} />
      </View>

      <View style={styles.stages}>
        {STAGES.map((s, i) => (
          <StageRow
            key={s.key}
            active={i === stageIdx}
            done={i < stageIdx || jobStatus === 'COMPLETED'}
            label={s.label}
            dark={!!dark}
          />
        ))}
      </View>

      <Text style={[styles.eta, { color: secondary }]}>
        Usually takes about 30 seconds
      </Text>
    </View>
  );
}

function StageRow({
  active,
  done,
  label,
  dark,
}: {
  active: boolean;
  done: boolean;
  label: string;
  dark: boolean;
}) {
  const dotBg = done
    ? colors.success
    : active
    ? colors.accent
    : dark
    ? colors.darkSurfaceAlt
    : colors.surfaceAlt;

  const borderColor = done
    ? colors.success
    : active
    ? colors.accent
    : dark
    ? colors.darkBorder
    : colors.border;

  const labelColor = done || active
    ? dark
      ? colors.darkTextPrimary
      : colors.textPrimary
    : dark
    ? colors.darkTextMuted
    : colors.textMuted;

  const iconColor = done || active
    ? colors.textOnDark
    : 'transparent';

  return (
    <View style={styles.stageRow}>
      <View style={[styles.stageDot, { backgroundColor: dotBg, borderColor }]}>
        {done && <Text style={[styles.stageCheck, { color: iconColor }]}>✓</Text>}
        {active && !done && (
          <View style={styles.stageActiveInner} />
        )}
      </View>
      <Text style={[styles.stageLabel, { color: labelColor }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, alignItems: 'center' },
  title: {
    fontSize: typography.fontSize.heading,
    fontWeight: '800',
    marginTop: spacing.lg,
    letterSpacing: typography.letterSpacing.tight,
  },
  sub: {
    fontSize: typography.fontSize.bodySmall,
    marginHorizontal: spacing.xl,
    textAlign: 'center',
    marginTop: spacing.sm,
  },
  visual: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginTop: spacing.xl,
  },
  imgCard: {
    width: 120,
    height: 150,
    borderRadius: radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    ...shadows.card,
  },
  img: { width: '100%', height: '100%' },
  plusBadge: {
    width: 40,
    height: 40,
    borderRadius: radius.full,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    ...shadows.accent,
  },
  plusText: {
    color: colors.primary,
    fontSize: 20,
    fontWeight: '800',
  },
  stages: {
    marginTop: spacing.xl,
    gap: spacing.md,
    width: '100%',
    paddingHorizontal: spacing.xl,
  },
  progressWrap: {
    width: '100%',
    paddingHorizontal: spacing.xl,
    marginTop: spacing.xl,
  },
  stageRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  stageDot: {
    width: 28,
    height: 28,
    borderRadius: radius.full,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stageCheck: {
    fontSize: 13,
    fontWeight: '800',
  },
  stageActiveInner: {
    width: 10,
    height: 10,
    borderRadius: radius.full,
    backgroundColor: colors.primary,
  },
  stageLabel: {
    fontSize: typography.fontSize.body,
    fontWeight: '600',
  },
  eta: {
    position: 'absolute',
    bottom: 60,
    fontSize: typography.fontSize.caption,
    fontWeight: '500',
  },
});
