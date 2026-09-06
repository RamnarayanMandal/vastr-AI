import React, { useRef, useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  useColorScheme,
  Platform,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTryOn } from '../../src/context/TryOnContext';
import { colors, radius, spacing, typography, shadows } from '../../src/theme';
import AppButton from '../../src/components/AppButton';
import UploadIndicator from '../../src/components/UploadIndicator';
import { UploadProgress } from '../../src/api/upload.api';
import * as ImagePicker from 'expo-image-picker';

export default function PersonCameraScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const cameraRef = useRef<CameraView | null>(null);
  const { uploadPerson } = useTryOn();
  const [permission, requestPermission] = useCameraPermissions();
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const scheme = useColorScheme();
  const dark = scheme === 'dark';

  const bg = dark ? colors.darkBackground : colors.background;
  const surface = dark ? colors.darkSurface : colors.surface;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const overlayBg = dark ? 'rgba(18,16,27,0.65)' : 'rgba(13,11,26,0.45)';
  const guideBorderColor = dark ? 'rgba(255,255,255,0.45)' : 'rgba(255,255,255,0.6)';

  const doUpload = async (uri: string) => {
    setBusy(true);
    setProgress({ loaded: 0, total: 1, percent: 0 });
    try {
      await uploadPerson(uri, setProgress);
      router.replace('/camera/fabric');
    } catch (e: any) {
      alert(e.message);
      setProgress(null);
    } finally {
      setBusy(false);
    }
  };

  const takePhoto = async () => {
    if (!cameraRef.current || busy) return;
    const photo = await cameraRef.current.takePictureAsync({ quality: 1 });
    if (photo?.uri) {
      await doUpload(photo.uri);
    }
  };

  const pickGallery = async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) return alert('Photo library permission is required.');
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 1,
    });
    if (result.canceled) return;
    await doUpload(result.assets[0].uri);
  };

  if (!permission) {
    return <View style={[styles.screen, { backgroundColor: bg }]} />;
  }

  if (!permission.granted) {
    return (
      <View
        style={[
          styles.screen,
          {
            backgroundColor: bg,
            alignItems: 'center',
            justifyContent: 'center',
            padding: spacing.xl,
          },
        ]}
      >
        <View style={[styles.permissionIconWrap, { backgroundColor: dark ? colors.darkSurfaceAlt : colors.accentSoft }]}>
          <Text style={styles.permissionIcon}>📸</Text>
        </View>
        <Text style={[styles.permissionTitle, { color: text }]}>
          Camera access needed
        </Text>
        <Text style={[styles.permissionSub, { color: secondary }]}>
          Allow camera to capture your photo for a virtual try-on.
        </Text>
        <View style={styles.permissionBtnWrap}>
          <AppButton title="Grant Camera Access" onPress={() => requestPermission()} />
          <View style={{ marginTop: spacing.sm }}>
            <AppButton
              title="Upload From Gallery"
              variant="outline"
              onPress={pickGallery}
            />
          </View>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.flex}>
      <CameraView ref={cameraRef} style={styles.camera} facing="front">
        <View style={[styles.topBar, { paddingTop: insets.top + spacing.md }]}>
          <TouchableOpacity
            onPress={() => router.back()}
            style={[styles.closeBtn, { backgroundColor: overlayBg }]}
          >
            <Text style={styles.closeIcon}>✕</Text>
          </TouchableOpacity>
          <Text style={styles.title}>Your Photo</Text>
          <View style={{ width: 40 }} />
        </View>

        <View style={styles.guideArea}>
          <View style={[styles.guideBox, { borderColor: guideBorderColor }]}>
            <View style={[styles.guideHead, { borderColor: guideBorderColor }]} />
            <View style={[styles.guideBody, { borderColor: guideBorderColor }]} />
          </View>
          <View style={[styles.guideTextWrap, { backgroundColor: overlayBg }]}>
            <Text style={styles.guideText}>
              Stand straight and keep your upper body visible.
            </Text>
          </View>
        </View>

        <View style={styles.spacer} />

        <View style={[styles.controlsWrap, { paddingBottom: insets.bottom + spacing.lg }]}>
          <View style={styles.controls}>
            <TouchableOpacity style={styles.galleryBtn} onPress={pickGallery}>
              <View style={[styles.galleryIconWrap, { backgroundColor: overlayBg }]}>
                <Text style={styles.galleryIcon}>🖼️</Text>
              </View>
              <Text style={styles.galleryLabel}>Gallery</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.shutterOuter, busy && styles.shutterDisabled]}
              onPress={takePhoto}
              disabled={busy}
            >
              <View style={styles.shutterInner} />
            </TouchableOpacity>

            <View style={{ width: 64 }} />
          </View>
        </View>
      </CameraView>

      {progress && (
        <UploadIndicator progress={progress} label="Uploading your photo" dark />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  screen: { flex: 1 },
  camera: { flex: 1 },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
  },
  closeBtn: {
    width: 40,
    height: 40,
    borderRadius: radius.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
  closeIcon: { color: '#fff', fontSize: 16, fontWeight: '700' },
  title: {
    color: '#fff',
    fontSize: typography.fontSize.body,
    fontWeight: '700',
    letterSpacing: typography.letterSpacing.wide,
  },
  guideArea: { alignItems: 'center', marginTop: spacing.xxl },
  guideBox: {
    width: 200,
    height: 260,
    borderWidth: 2,
    borderRadius: radius.xl,
    alignItems: 'center',
    paddingTop: 22,
  },
  guideHead: {
    width: 44,
    height: 44,
    borderRadius: radius.full,
    borderWidth: 2,
  },
  guideBody: {
    width: 30,
    height: 60,
    borderRadius: 15,
    borderWidth: 2,
    marginTop: 14,
  },
  guideTextWrap: {
    marginTop: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: radius.full,
    overflow: 'hidden',
  },
  guideText: {
    color: '#fff',
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '500',
    textAlign: 'center',
  },
  spacer: { flex: 1 },
  controlsWrap: {
    paddingHorizontal: spacing.xl,
  },
  controls: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
  },
  galleryBtn: { alignItems: 'center', width: 64 },
  galleryIconWrap: {
    width: 48,
    height: 48,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  galleryIcon: { fontSize: 22 },
  galleryLabel: {
    color: '#fff',
    fontSize: typography.fontSize.micro,
    fontWeight: '600',
    marginTop: spacing.xs,
  },
  shutterOuter: {
    width: 76,
    height: 76,
    borderRadius: radius.full,
    borderWidth: 4,
    borderColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  shutterInner: {
    width: 60,
    height: 60,
    borderRadius: radius.full,
    backgroundColor: '#fff',
  },
  shutterDisabled: { opacity: 0.45 },
  permissionIconWrap: {
    width: 88,
    height: 88,
    borderRadius: radius.full,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  permissionIcon: { fontSize: 38 },
  permissionTitle: {
    fontSize: typography.fontSize.heading,
    fontWeight: '800',
    textAlign: 'center',
  },
  permissionSub: {
    fontSize: typography.fontSize.bodySmall,
    textAlign: 'center',
    marginTop: spacing.sm,
    lineHeight: typography.lineHeight.bodySmall,
  },
  permissionBtnWrap: { width: '100%', marginTop: spacing.lg },
});
