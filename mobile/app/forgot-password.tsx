import React, { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  useColorScheme,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import AppButton from '../src/components/AppButton';
import { useForgotPasswordMutation } from '../src/hooks/mutations';
import { parseApiError } from '../src/api/errors';
import { colors, radius, spacing, typography, shadows } from '../src/theme';

export default function ForgotPasswordScreen() {
  const router = useRouter();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  const [email, setEmail] = useState('');
  const forgotMutation = useForgotPasswordMutation();

  const bg = dark ? colors.darkBackground : colors.background;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const inputBg = dark ? colors.darkSurface : colors.surface;
  const inputBorder = dark ? colors.darkBorder : colors.border;

  const submit = async () => {
    if (!email.trim()) {
      alert('Please enter your email address.');
      return;
    }
    try {
      await forgotMutation.mutateAsync(email.trim());
      alert('If the email is registered, a reset OTP has been sent.');
      router.replace('/reset-password');
    } catch (e: unknown) {
      alert(parseApiError(e).message);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={[styles.screen, { backgroundColor: bg }]}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
          <Text style={[styles.backArrow, { color: text }]}>‹</Text>
        </TouchableOpacity>

        <View style={styles.brand}>
          <View style={styles.logoBadge}>
            <Text style={styles.logoIcon}>✦</Text>
          </View>
          <Text style={[styles.logo, { color: text }]}>VastrAI</Text>
          <Text style={[styles.tagline, { color: secondary }]}>See It. Try It. Wear It.</Text>
        </View>

        <Text style={[styles.heading, { color: text }]}>Reset your password</Text>
        <Text style={[styles.subtitle, { color: secondary }]}>
          Enter your email and we will send a six-digit OTP through Gmail.
        </Text>

        <View style={styles.form}>
          <Text style={[styles.label, { color: secondary }]}>Email</Text>
          <TextInput
            style={[styles.input, { backgroundColor: inputBg, borderColor: inputBorder, color: text }]}
            value={email}
            onChangeText={setEmail}
            placeholder="you@example.com"
            placeholderTextColor={colors.textMuted}
            autoCapitalize="none"
            keyboardType="email-address"
            autoFocus
          />

          <View style={styles.ctaWrap}>
            <AppButton
              title="Send OTP"
              variant="accent"
              onPress={submit}
              loading={forgotMutation.isPending}
            />
          </View>
        </View>

        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.link}>Back to login</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl,
  },
  backBtn: {
    marginBottom: spacing.sm,
    alignSelf: 'flex-start',
  },
  backArrow: {
    fontSize: 28,
    fontWeight: '600',
    paddingLeft: spacing.xs,
  },
  brand: {
    alignItems: 'center',
    marginBottom: spacing.xl,
  },
  logoBadge: {
    width: 64,
    height: 64,
    borderRadius: radius.lg,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
    ...shadows.accent,
  },
  logoIcon: {
    fontSize: 24,
    color: colors.primary,
    fontWeight: '700',
  },
  logo: {
    fontSize: typography.fontSize.title,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  tagline: {
    fontSize: typography.fontSize.bodySmall,
    marginTop: spacing.xs,
    letterSpacing: typography.letterSpacing.wide,
  },
  heading: {
    fontSize: typography.fontSize.heading,
    fontWeight: '700',
    marginTop: spacing.lg,
  },
  subtitle: {
    fontSize: typography.fontSize.bodySmall,
    marginTop: spacing.xs,
    marginBottom: spacing.lg,
    lineHeight: typography.lineHeight.bodySmall,
  },
  form: {
    gap: spacing.md,
  },
  label: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '600',
    marginBottom: spacing.xs,
  },
  input: {
    borderWidth: 1,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: 14,
    fontSize: typography.fontSize.body,
  },
  ctaWrap: {
    marginTop: spacing.sm,
  },
  link: {
    color: colors.accentDark,
    fontWeight: '700',
    fontSize: typography.fontSize.bodySmall,
    textAlign: 'center',
    marginTop: spacing.xl,
  },
});