import React, { useEffect } from 'react';
import { StyleSheet, Text, View, Animated } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../src/context/AuthContext';
import { colors, radius, spacing, typography, shadows } from '../src/theme';

export default function SplashScreen() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const fade = React.useRef(new Animated.Value(0)).current;
  const scale = React.useRef(new Animated.Value(0.88)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fade, { toValue: 1, duration: 800, useNativeDriver: true }),
      Animated.spring(scale, { toValue: 1, friction: 5, tension: 40, useNativeDriver: true }),
    ]).start();
  }, []);

  useEffect(() => {
    if (!loading) {
      const timer = setTimeout(() => {
        router.replace(user ? '/(tabs)/home' : '/login');
      }, 1600);
      return () => clearTimeout(timer);
    }
  }, [loading, user]);

  return (
    <View style={styles.container}>
      <Animated.View style={[styles.inner, { opacity: fade, transform: [{ scale }] }]}>
        <View style={styles.logoBadge}>
          <Text style={styles.logoIcon}>✦</Text>
        </View>

        <Text style={styles.brand}>VastrAI</Text>

        <View style={styles.divider} />

        <Text style={styles.tagline}>See It. Try It. Wear It.</Text>

        <View style={styles.sparkleRow}>
          <Text style={styles.sparkle}>✦</Text>
          <Text style={styles.sparkleSm}>✦</Text>
          <Text style={styles.sparkle}>✦</Text>
        </View>
      </Animated.View>

      <Text style={styles.footer}>AI VIRTUAL TRY-ON</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  inner: {
    alignItems: 'center',
  },
  logoBadge: {
    width: 88,
    height: 88,
    borderRadius: radius.xl,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.accent,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.45,
    shadowRadius: 24,
    elevation: 10,
  },
  logoIcon: {
    fontSize: 36,
    color: colors.primary,
    fontWeight: '700',
  },
  brand: {
    fontSize: typography.fontSize.display + 4,
    fontWeight: '800',
    color: colors.textOnDark,
    marginTop: spacing.lg,
    letterSpacing: typography.letterSpacing.wide,
  },
  divider: {
    width: 48,
    height: 2,
    backgroundColor: colors.accent,
    borderRadius: radius.full,
    marginVertical: spacing.md,
  },
  tagline: {
    fontSize: typography.fontSize.subheading,
    color: colors.textOnDarkMuted,
    letterSpacing: 0.6,
    fontWeight: '500',
  },
  sparkleRow: {
    flexDirection: 'row',
    gap: 14,
    marginTop: spacing.xl,
    alignItems: 'center',
  },
  sparkle: {
    color: colors.accent,
    fontSize: 14,
  },
  sparkleSm: {
    color: colors.accent,
    fontSize: 9,
    opacity: 0.6,
  },
  footer: {
    position: 'absolute',
    bottom: spacing.xxl,
    fontSize: typography.fontSize.caption,
    color: colors.textOnDarkMuted,
    letterSpacing: typography.letterSpacing.widest,
    textTransform: 'uppercase',
    fontWeight: '600',
  },
});
