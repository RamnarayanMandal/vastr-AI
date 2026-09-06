import React from 'react';
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
import { useAuth } from '../../src/context/AuthContext';
import { colors, radius, spacing, typography, shadows } from '../../src/theme';
import BottomNav from '../../src/components/BottomNav';
import { Alert } from 'react-native';
import { useDeactivateAccountMutation, useDeleteAccountMutation } from '../../src/hooks/mutations';
import { queryClient } from '../../src/query/QueryProvider';

const options = [
  { label: 'Account', emoji: '◉', route: '/account' },
  { label: 'AI Credits', emoji: '✦', route: '/credits' },
  { label: 'Notifications', emoji: '🔔', route: '/notifications' },
  { label: 'Privacy Policy', emoji: '🔒', route: '/privacy' },
  { label: 'Help & Support', emoji: '❓', route: '/help-support' },
  { label: 'Deactivate Account', emoji: '⏸', action: 'deactivate' },
  { label: 'Delete My Account', emoji: '⌫', action: 'delete', danger: true },
  { label: 'Log Out', emoji: '🚪', danger: true },
];

export default function ProfileScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { user, signOut } = useAuth();
  const deactivateMutation = useDeactivateAccountMutation();
  const deleteMutation = useDeleteAccountMutation();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';

  const bg = dark ? colors.darkBackground : colors.background;
  const surface = dark ? colors.darkSurface : colors.surface;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;
  const border = dark ? colors.darkBorder : colors.border;

  const initials = (user?.full_name ?? 'V')
    .split(' ')
    .map((w: string) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={[styles.header, { paddingTop: insets.top + spacing.xl }]}>
          <Text style={[styles.title, { color: text }]}>Profile</Text>
        </View>

        <View style={[styles.profileCard, { backgroundColor: surface, borderColor: border }]}>
          <View style={styles.avatarCircle}>
            <Text style={styles.avatarInitials}>{initials}</Text>
          </View>
          <Text style={[styles.userName, { color: text }]}>
            {user?.full_name ?? 'VastrAI User'}
          </Text>
          <Text style={[styles.userEmail, { color: secondary }]}>
            {user?.email ?? 'user@vastrai.app'}
          </Text>
          {user?.mobile ? (
            <Text style={[styles.userPhone, { color: secondary }]}>{user.mobile}</Text>
          ) : null}
        </View>

        <View style={styles.optionsList}>
          {options.map((opt, idx) => (
            <TouchableOpacity
              key={opt.label}
              style={[
                styles.optionRow,
                {
                  backgroundColor: surface,
                  borderColor: border,
                  marginTop: idx === 0 ? 0 : spacing.sm,
                },
              ]}
              activeOpacity={0.65}
              onPress={() => {
                if (opt.action === 'deactivate') {
                  Alert.alert('Deactivate account', 'Your account will be blocked until reactivated.', [
                    { text: 'Cancel', style: 'cancel' },
                    { text: 'Deactivate', style: 'destructive', onPress: async () => { await deactivateMutation.mutateAsync(); queryClient.clear(); await signOut(); router.replace('/login'); } },
                  ]);
                } else if (opt.action === 'delete') {
                  Alert.alert('Delete account', 'This permanently removes your account and application records.', [
                    { text: 'Cancel', style: 'cancel' },
                    { text: 'Delete', style: 'destructive', onPress: async () => { await deleteMutation.mutateAsync(); queryClient.clear(); await signOut(); router.replace('/login'); } },
                  ]);
                } else if (opt.route) {
                  router.push(opt.route as any);
                } else if (opt.label === 'Log Out') {
                  signOut().then(() => router.replace('/login'));
                } else {
                  router.push('/history');
                }
              }}
            >
              <View style={styles.optionLeft}>
                <Text style={styles.optionEmoji}>{opt.emoji}</Text>
                <Text
                  style={[
                    styles.optionLabel,
                    { color: opt.danger ? colors.danger : text },
                  ]}
                >
                  {opt.label}
                </Text>
              </View>
              <Text style={[styles.chevron, { color: secondary }]}>›</Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={[styles.versionText, { color: secondary }]}>
          VastrAI v1.0.0
        </Text>
      </ScrollView>
      <BottomNav />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  scrollContent: { paddingBottom: 40 },
  header: { paddingHorizontal: spacing.lg },
  title: {
    fontSize: typography.fontSize.title,
    fontWeight: '800',
    letterSpacing: typography.letterSpacing.tight,
  },
  profileCard: {
    marginHorizontal: spacing.lg,
    marginTop: spacing.lg,
    borderRadius: radius.xl,
    borderWidth: 1,
    padding: spacing.xl,
    alignItems: 'center',
    ...shadows.card,
  },
  avatarCircle: {
    width: 88,
    height: 88,
    borderRadius: radius.full,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    ...shadows.accent,
  },
  avatarInitials: {
    fontSize: 36,
    fontWeight: '800',
    color: colors.primary,
    letterSpacing: 1,
  },
  userName: {
    fontSize: typography.fontSize.heading,
    fontWeight: '700',
    marginTop: spacing.md,
    letterSpacing: typography.letterSpacing.tight,
  },
  userEmail: {
    fontSize: typography.fontSize.bodySmall,
    marginTop: 4,
  },
  userPhone: {
    fontSize: typography.fontSize.bodySmall,
    marginTop: 2,
  },
  optionsList: {
    padding: spacing.lg,
    paddingTop: spacing.md,
  },
  optionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.md + 2,
    paddingHorizontal: spacing.lg,
  },
  optionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  optionEmoji: { fontSize: 20 },
  optionLabel: {
    fontSize: typography.fontSize.body,
    fontWeight: '600',
  },
  chevron: {
    fontSize: 20,
    fontWeight: '300',
  },
  versionText: {
    textAlign: 'center',
    marginTop: spacing.xl,
    fontSize: typography.fontSize.caption,
    letterSpacing: typography.letterSpacing.wide,
  },
});
