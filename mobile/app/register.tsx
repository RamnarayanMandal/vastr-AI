import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  TextInput,
  View,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity,
  useColorScheme,
} from 'react-native';
import { useRouter } from 'expo-router';
import AppButton from '../src/components/AppButton';
import { useAuth } from '../src/context/AuthContext';
import { colors, radius, spacing, typography, shadows } from '../src/theme';
import { useRegisterMutation } from '../src/hooks/mutations';
import { parseApiError } from '../src/api/errors';

export default function RegisterScreen() {
  const router = useRouter();
  const { signIn } = useAuth();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  const [fullName, setFullName] = useState('');
  const [mobile, setMobile] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const registerMutation = useRegisterMutation();

  const bg = dark ? colors.darkBackground : colors.background;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const inputBg = dark ? colors.darkSurface : colors.surface;
  const inputBorder = dark ? colors.darkBorder : colors.border;

  const onRegister = async () => {
    if (password !== confirm) {
      alert('Passwords do not match.');
      return;
    }
    try {
      const data = await registerMutation.mutateAsync({ full_name: fullName, mobile, email, password });
      await signIn(data.access_token, data.user);
      router.replace('/(tabs)/home');
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
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Text style={[styles.backArrow, { color: text }]}>‹</Text>
        </TouchableOpacity>

        <Text style={[styles.heading, { color: text }]}>Create Account</Text>
        <Text style={[styles.subtitle, { color: secondary }]}>Join VastrAI and try before you buy</Text>

        <View style={styles.form}>
          <Text style={[styles.label, { color: secondary }]}>Full Name</Text>
          <TextInput
            style={[styles.input, { backgroundColor: inputBg, borderColor: inputBorder, color: text }]}
            value={fullName}
            onChangeText={setFullName}
            placeholder="Your name"
            placeholderTextColor={colors.textMuted}
          />

          <Text style={[styles.label, { color: secondary }]}>Mobile Number</Text>
          <TextInput
            style={[styles.input, { backgroundColor: inputBg, borderColor: inputBorder, color: text }]}
            value={mobile}
            onChangeText={setMobile}
            placeholder="+91 ..."
            placeholderTextColor={colors.textMuted}
            keyboardType="phone-pad"
          />

          <Text style={[styles.label, { color: secondary }]}>Email</Text>
          <TextInput
            style={[styles.input, { backgroundColor: inputBg, borderColor: inputBorder, color: text }]}
            value={email}
            onChangeText={setEmail}
            placeholder="you@example.com"
            placeholderTextColor={colors.textMuted}
            autoCapitalize="none"
            keyboardType="email-address"
          />

          <Text style={[styles.label, { color: secondary }]}>Password</Text>
          <View style={styles.passwordWrap}>
            <TextInput
              style={[styles.input, styles.passwordInput, { backgroundColor: inputBg, borderColor: inputBorder, color: text }]}
              value={password}
              onChangeText={setPassword}
              placeholder="Min 6 characters"
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
              placeholder="Re-enter password"
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
            <AppButton title="Create Account" variant="accent" onPress={onRegister} loading={registerMutation.isPending} />
          </View>

          <View style={styles.dividerRow}>
            <View style={[styles.dividerLine, { backgroundColor: inputBorder }]} />
            <Text style={[styles.dividerText, { color: secondary }]}>or</Text>
            <View style={[styles.dividerLine, { backgroundColor: inputBorder }]} />
          </View>

          <AppButton
            title="Sign up with Google"
            variant="outline"
            onPress={() => alert('Google sign-up coming soon.')}
          />
        </View>

        <Text style={[styles.terms, { color: secondary }]}>
          By creating an account you agree to our{' '}
          <Text style={styles.termsLink}>Terms of Service</Text>
          {' '}and{' '}
          <Text style={styles.termsLink}>Privacy Policy</Text>.
        </Text>

        <View style={styles.footer}>
          <Text style={[styles.footerText, { color: secondary }]}>Already have an account? </Text>
          <TouchableOpacity onPress={() => router.replace('/login')}>
            <Text style={styles.link}>Login</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xxl,
    paddingBottom: spacing.xl,
  },
  backBtn: {
    marginBottom: spacing.lg,
    alignSelf: 'flex-start',
  },
  backArrow: {
    fontSize: 28,
    fontWeight: '600',
    paddingLeft: spacing.xs,
  },
  heading: {
    fontSize: typography.fontSize.title,
    fontWeight: '800',
    marginBottom: spacing.xs,
  },
  subtitle: {
    fontSize: typography.fontSize.bodySmall,
    marginBottom: spacing.lg,
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
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginVertical: spacing.xs,
  },
  dividerLine: {
    flex: 1,
    height: 1,
  },
  dividerText: {
    fontSize: typography.fontSize.bodySmall,
  },
  terms: {
    fontSize: typography.fontSize.caption,
    textAlign: 'center',
    marginTop: spacing.lg,
    lineHeight: typography.lineHeight.caption,
  },
  termsLink: {
    color: colors.accentDark,
    fontWeight: '600',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: spacing.xl,
  },
  footerText: {
    fontSize: typography.fontSize.bodySmall,
  },
  link: {
    color: colors.accentDark,
    fontWeight: '700',
    fontSize: typography.fontSize.bodySmall,
  },
});
