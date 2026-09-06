import React from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  useColorScheme,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTryOn } from '../../src/context/TryOnContext';
import { colors, radius, spacing, typography } from '../../src/theme';
import AppButton from '../../src/components/AppButton';

export default function ProcessingErrorScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { draft, reset } = useTryOn();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';

  const bg = dark ? colors.darkBackground : colors.background;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const iconBg = dark ? colors.darkSurfaceAlt : colors.dangerSoft;

  // Show the actual backend error if available
  const backendError = draft.error || null;

  const onRetry = () => {
    reset();
    router.replace('/camera/person');
  };

  const onChangeImage = () => {
    reset();
    router.replace('/tryon/upload');
  };

  return (
    <View
      style={[
        styles.screen,
        { backgroundColor: bg, paddingTop: insets.top + spacing.xl },
      ]}
    >
      <View style={styles.center}>
        <View style={[styles.iconWrap, { backgroundColor: iconBg }]}>
          <Text style={styles.icon}>🔧</Text>
        </View>
        <Text style={[styles.title, { color: text }]}>
          We couldn't create your look this time
        </Text>
        {backendError ? (
          <Text style={[styles.backendError, { color: colors.danger }]}>
            {backendError}
          </Text>
        ) : (
          <Text style={[styles.sub, { color: secondary }]}>
            Something went wrong during the AI creation. Please try again.
          </Text>
        )}

        <View style={styles.btnWrap}>
          <AppButton title="Try Again" onPress={onRetry} />
          <View style={{ marginTop: spacing.sm }}>
            <AppButton
              title="Change Image"
              variant="outline"
              onPress={onChangeImage}
            />
          </View>
        </View>

        <TouchableOpacity
          onPress={() => router.replace('/(tabs)/home')}
          style={styles.homeLinkWrap}
        >
          <Text style={[styles.homeLink, { color: secondary }]}>
            Back to Home
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
  },
  iconWrap: {
    width: 88,
    height: 88,
    borderRadius: radius.full,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  icon: { fontSize: 38 },
  title: {
    fontSize: typography.fontSize.heading,
    fontWeight: '800',
    textAlign: 'center',
    letterSpacing: typography.letterSpacing.tight,
  },
  sub: {
    fontSize: typography.fontSize.bodySmall,
    textAlign: 'center',
    marginTop: spacing.sm,
    maxWidth: 300,
    lineHeight: typography.lineHeight.bodySmall,
  },
  backendError: {
    fontSize: typography.fontSize.bodySmall,
    textAlign: 'center',
    marginTop: spacing.sm,
    maxWidth: 320,
    lineHeight: typography.lineHeight.bodySmall,
    fontWeight: '600',
  },
  btnWrap: { width: '100%', marginTop: spacing.xl },
  homeLinkWrap: { marginTop: spacing.xl },
  homeLink: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '700',
  },
});
