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
import { useLoginMutation } from '../src/hooks/mutations';
import { parseApiError } from '../src/api/errors';

export default function LoginScreen() {
  const router = useRouter();
  const { signIn } = useAuth();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const loginMutation = useLoginMutation();

  const onLogin = async () => {
    try {
      const data = await loginMutation.mutateAsync({ identifier, password });
      await signIn(data.access_token, data.user);
      router.replace('/(tabs)/home');
    } catch (e: any) {
      alert(parseApiError(e).message);
    }
  };

  const bg = dark ? colors.darkBackground : colors.background;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const inputBg = dark ? colors.darkSurface : colors.surface;
  const inputBorder = dark ? colors.darkBorder : colors.border;

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={[styles.screen, { backgroundColor: bg }]}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.brand}>
          <View style={styles.logoBadge}>
            <Text style={styles.logoIcon}>✦</Text>
          </View>
          <Text style={[styles.logo, { color: text }]}>VastrAI</Text>
          <Text style={[styles.tagline, { color: secondary }]}>See It. Try It. Wear It.</Text>
        </View>

        <Text style={[styles.welcome, { color: text }]}>Welcome Back</Text>
        <Text style={[styles.subtitle, { color: secondary }]}>Sign in to continue your try-ons</Text>

        <View style={styles.form}>
          <Text style={[styles.label, { color: secondary }]}>Email or Mobile Number</Text>
          <TextInput
            style={[styles.input, { backgroundColor: inputBg, borderColor: inputBorder, color: text }]}
            value={identifier}
            onChangeText={setIdentifier}
            placeholder="you@example.com or +91..."
            placeholderTextColor={colors.textMuted}
            autoCapitalize="none"
            keyboardType="email-address"
          />

          <View style={styles.passwordRow}>
            <Text style={[styles.label, { color: secondary }]}>Password</Text>
            <TouchableOpacity onPress={() => router.push('/forgot-password')}>
              <Text style={styles.forgot}>Forgot Password?</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.passwordWrap}>
            <TextInput
              style={[styles.input, styles.passwordInput, { backgroundColor: inputBg, borderColor: inputBorder, color: text }]}
              value={password}
              onChangeText={setPassword}
              placeholder="Your password"
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

          <View style={styles.ctaWrap}>
            <AppButton title="Login" variant="accent" onPress={onLogin} loading={loginMutation.isPending} />
          </View>

          <View style={styles.dividerRow}>
            <View style={[styles.dividerLine, { backgroundColor: inputBorder }]} />
            <Text style={[styles.dividerText, { color: secondary }]}>or</Text>
            <View style={[styles.dividerLine, { backgroundColor: inputBorder }]} />
          </View>

          <AppButton
            title="Continue with Google"
            variant="outline"
            onPress={() => alert('Google sign-in coming soon.')}
          />
        </View>

        <View style={styles.footer}>
          <Text style={[styles.footerText, { color: secondary }]}>Don't have an account? </Text>
          <TouchableOpacity onPress={() => router.push('/register')}>
            <Text style={styles.link}>Create Account</Text>
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
    paddingTop: spacing.xxxl,
    paddingBottom: spacing.xl,
    justifyContent: 'center',
  },
  brand: {
    alignItems: 'center',
    marginBottom: spacing.xxl,
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
  welcome: {
    fontSize: typography.fontSize.heading,
    fontWeight: '700',
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
  passwordRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
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
  forgot: {
    color: colors.accentDark,
    fontWeight: '700',
    fontSize: typography.fontSize.bodySmall,
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
