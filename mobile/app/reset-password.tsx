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
import { useResetPasswordMutation } from '../src/hooks/mutations';
import { parseApiError } from '../src/api/errors';
import { colors, radius, spacing, typography, shadows } from '../src/theme';

export default function ResetPasswordScreen() {
  const router = useRouter();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  const [otp, setOtp] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const resetMutation = useResetPasswordMutation();

  const bg = dark ? colors.darkBackground : colors.background;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const inputBg = dark ? colors.darkSurface : colors.surface;
  const inputBorder = dark ? colors.darkBorder : colors.border;

  const submit = async () => {
    if (otp.length !== 6) {
      alert('Enter the six-digit OTP sent to your email.');
      return;
    }
    if (password.length < 8) {
      alert('New password must be at least 8 characters long.');
      return;
    }
    if (password !== confirm) {
      alert('Passwords do not match.');
      return;
    }
    try {
      await resetMutation.mutateAsync({ otp, newPassword: password });
      alert('Password changed successfully.');
      router.replace('/login');
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
        <TouchableOpacity onPress={() => router.replace('/login')} style={styles.backBtn} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
          <Text style={[styles.backArrow, { color: text }]}>‹</Text>
        </TouchableOpacity>

        <View style={styles.brand}>
          <View style={styles.logoBadge}>
            <Text style={styles.logoIcon}>✦</Text>
          </View>
          <Text style={[styles.logo, { color: text }]}>VastrAI</Text>
          <Text style={[styles.tagline, { color: secondary }]}>See It. Try It. Wear It.</Text>
        </View>

        <Text style={[styles.heading, { color: text }]}>Enter your OTP</Text>
        <Text style={[styles.subtitle, { color: secondary }]}>
          Enter the six-digit code sent to your email, then choose a new password.
        </Text>

        <View style={styles.form}>
          <Text style={[styles.label, { color: secondary }]}>One-Time Password</Text>
          <TextInput
            style={[styles.input, { backgroundColor: inputBg, borderColor: inputBorder, color: text }]}
            value={otp}
            onChangeText={setOtp}
            placeholder="000000"
            placeholderTextColor={colors.textMuted}
            keyboardType="number-pad"
            maxLength={6}
          />

          <Text style={[styles.label, { color: secondary }]}>New Password</Text>
          <View style={styles.passwordWrap}>
            <TextInput
              style={[styles.input, styles.passwordInput, { backgroundColor: inputBg, borderColor: inputBorder, color: text }]}
              value={password}
              onChangeText={setPassword}
              placeholder="Min 8 characters"
              placeholderTextColor={colors.textMuted}
              secureTextEntry={!showPassword}
            />
            <TouchableOpacity
              style={styles.eyeBtn}
              onPress={() => setShowPassword((v) => !v)}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            >
              <Text style={styles.eyeIcon}>{showPassword ? '🙈' : '👁'}</Text>
            </TouchableOpacity>
          </View>

          <Text style={[styles.label, { color: secondary }]}>Confirm Password</Text>
          <View style={styles.passwordWrap}>
            <TextInput
              style={[styles.input, styles.passwordInput, { backgroundColor: inputBg, borderColor: inputBorder, color: text }]}
              value={confirm}
              onChangeText={setConfirm}
              placeholder="Re-enter new password"
              placeholderTextColor={colors.textMuted}
              secureTextEntry={!showConfirm}
            />
            <TouchableOpacity
              style={styles.eyeBtn}
              onPress={() => setShowConfirm((v) => !v)}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            >
              <Text style={styles.eyeIcon}>{showConfirm ? '🙈' : '👁'}</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.ctaWrap}>
            <AppButton
              title="Change password"
              variant="accent"
              onPress={submit}
              loading={resetMutation.isPending}
            />
          </View>
        </View>
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
  passwordWrap: {
    position: 'relative',
  },
  passwordInput: {
    paddingRight: spacing.xxxl,
  },
  eyeBtn: {
    position: 'absolute',
    right: spacing.md,
    top: 0,
    bottom: 0,
    justifyContent: 'center',
  },
  eyeIcon: {
    fontSize: 18,
  },
  ctaWrap: {
    marginTop: spacing.sm,
  },
});