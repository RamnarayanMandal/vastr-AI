import React, { useState } from 'react';
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
import * as ImagePicker from 'expo-image-picker';
import { useTryOn } from '../../src/context/TryOnContext';
import { colors, radius, spacing, typography } from '../../src/theme';
import ImageUploadCard from '../../src/components/ImageUploadCard';
import AppButton from '../../src/components/AppButton';
import UploadIndicator from '../../src/components/UploadIndicator';
import { UploadProgress } from '../../src/api/upload.api';

export default function UploadScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { draft, setDraft, uploadPerson, uploadFabric } = useTryOn();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';

  const bg = dark ? colors.darkBackground : colors.background;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;

  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);

  const pickImage = async (kind: 'person' | 'fabric') => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      alert('Photo library permission is required.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 1,
    });
    if (result.canceled) return;
    const uri = result.assets[0].uri;
    setBusy(true);
    setProgress({ loaded: 0, total: 1, percent: 0 });
    try {
      if (kind === 'person') {
        await uploadPerson(uri, setProgress);
      } else {
        await uploadFabric(uri, setProgress);
      }
    } catch (e: any) {
      alert(e.message);
      setProgress(null);
    } finally {
      setProgress(null);
      setBusy(false);
    }
  };

  const takePhoto = async (kind: 'person' | 'fabric') => {
    router.push(kind === 'person' ? '/camera/person' : '/camera/fabric');
  };

  const ready = !!draft.personImageUri && !!draft.fabricImageUri;

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <View style={{ paddingTop: insets.top + spacing.md }}>
        <TouchableOpacity onPress={() => router.back()} style={styles.back}>
          <Text style={{ color: text, fontSize: 24 }}>‹</Text>
        </TouchableOpacity>
        <Text style={[styles.title, { color: text }]}>Create Your Look</Text>
        <Text style={[styles.sub, { color: secondary }]}>Add your photo and your cloth. Two images, one look.</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <ImageUploadCard
          stepLabel="STEP 1"
          title="Your Photo"
          subtitle="Show your face and upper body"
          uri={draft.personImageUri}
          primaryLabel="Take Photo"
          secondaryLabel="Upload From Gallery"
          onPrimary={() => takePhoto('person')}
          onSecondary={() => pickImage('person')}
          onRetake={() => takePhoto('person')}
          onChange={() => pickImage('person')}
          onRemove={() => setDraft({ personImageUri: null, personImageId: null })}
        />

        <View style={styles.plusRow}>
          <View style={styles.plusLine} />
          <View style={styles.plusBadge}>
            <Text style={styles.plusText}>+</Text>
          </View>
          <View style={styles.plusLine} />
        </View>

        <ImageUploadCard
          stepLabel="STEP 2"
          title="Your Cloth / Garment"
          subtitle="Show the fabric or the garment"
          uri={draft.fabricImageUri}
          primaryLabel="Capture"
          secondaryLabel="Upload"
          onPrimary={() => takePhoto('fabric')}
          onSecondary={() => pickImage('fabric')}
          onRetake={() => takePhoto('fabric')}
          onChange={() => pickImage('fabric')}
          onRemove={() => setDraft({ fabricImageUri: null, fabricImageId: null })}
        />

        <View style={styles.progressCard}>
          <StatusRow ok={!!draft.personImageUri} label="Your photo" />
          <StatusRow ok={!!draft.fabricImageUri} label="Cloth / garment" />
          <StatusRow ok={!!draft.garmentId} label="Selected garment" />
        </View>
      </ScrollView>

      <View style={[styles.footer, { paddingBottom: insets.bottom + spacing.md }]}>
        <AppButton
          title="Continue"
          variant="accent"
          disabled={!ready}
          onPress={() => router.push('/tryon/style')}
        />
      </View>

      {busy && progress && (
        <UploadIndicator progress={progress} label="Uploading" />
      )}
    </View>
  );
}

function StatusRow({ ok, label }: { ok: boolean; label: string }) {
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  return (
    <View style={styles.statusRow}>
      <View style={[styles.statusDot, { backgroundColor: ok ? colors.success : (dark ? colors.darkBorder : colors.border) }]}>
        <Text style={{ color: ok ? colors.textOnDark : (dark ? colors.darkTextMuted : colors.textMuted), fontSize: 11, fontWeight: '800' }}>{ok ? '✓' : '✕'}</Text>
      </View>
      <Text style={[styles.statusLabel, { color: ok ? colors.success : (dark ? colors.darkTextMuted : colors.textMuted) }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  back: { alignSelf: 'flex-start', marginHorizontal: spacing.lg },
  title: { fontSize: typography.fontSize.title, fontWeight: '800', marginHorizontal: spacing.lg, marginTop: spacing.sm },
  sub: { fontSize: typography.fontSize.bodySmall, marginHorizontal: spacing.lg, marginTop: 4 },
  content: { padding: spacing.lg, gap: spacing.md },
  plusRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, marginVertical: spacing.xs },
  plusLine: { flex: 1, height: 1, backgroundColor: colors.border },
  plusBadge: {
    width: 32, height: 32, borderRadius: radius.full, backgroundColor: colors.accent,
    alignItems: 'center', justifyContent: 'center',
  },
  plusText: { color: colors.primary, fontSize: 18, fontWeight: '800' },
  progressCard: {
    borderRadius: radius.lg, backgroundColor: colors.accentSoft, padding: spacing.md, gap: spacing.sm,
  },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  statusDot: { width: 22, height: 22, borderRadius: radius.full, alignItems: 'center', justifyContent: 'center' },
  statusLabel: { fontSize: typography.fontSize.bodySmall, fontWeight: '600' },
  footer: { paddingHorizontal: spacing.lg, paddingTop: spacing.sm },
});