import React from 'react';
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  useColorScheme,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '../src/context/AuthContext';
import { useDeactivateAccountMutation, useDeleteAccountMutation } from '../src/hooks/mutations';
import { queryClient } from '../src/query/QueryProvider';
import { colors, radius, spacing, typography, shadows } from '../src/theme';

const menuOptions = [
  { label: 'Reset Password', emoji: '🔑', route: '/forgot-password' },
  { label: 'AI Credits', emoji: '✦', route: '/credits' },
  { label: 'Notifications', emoji: '🔔', route: '/notifications' },
  { label: 'Help & Support', emoji: '❓', route: '/help-support' },
  { label: 'Privacy Policy', emoji: '🔒', route: '/privacy' },
];

export default function AccountScreen() {
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

  const confirmAccountAction = (
    title: string,
    message: string,
    confirmLabel: string,
    onConfirm: () => Promise<unknown>,
  ) => {
    Alert.alert(title, message, [
      { text: 'Cancel', style: 'cancel' },
      { text: confirmLabel, style: 'destructive', onPress: async () => { await onConfirm(); queryClient.clear(); await signOut(); router.replace('/login'); } },
    ]);
  };

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={[styles.header, { paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg }]}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
            <Text style={[styles.backArrow, { color: text }]}>‹</Text>
          </TouchableOpacity>
          <Text style={[styles.title, { color: text }]}>Account</Text>
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
            <Text style={[styles.userDetail, { color: secondary }]}>{user.mobile}</Text>
          ) : null}
          <View style={[styles.statusChip, { backgroundColor: dark ? colors.darkSurfaceAlt : colors.accentSoft }]}>
            <Text style={styles.statusText}>{user?.status ?? 'ACTIVE'}</Text>
          </View>
        </View>

        <Text style={[styles.sectionLabel, { color: secondary }]}>Manage your account</Text>

        <View style={styles.optionsList}>
          {menuOptions.map((opt, idx) => (
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
              onPress={() => router.push(opt.route as never)}
            >
              <View style={styles.optionLeft}>
                <Text style={styles.optionEmoji}>{opt.emoji}</Text>
                <Text style={[styles.optionLabel, { color: text }]}>{opt.label}</Text>
              </View>
              <Text style={[styles.chevron, { color: secondary }]}>›</Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={[styles.sectionLabel, { color: secondary }]}>Account actions</Text>

        <View style={styles.optionsList}>
          <TouchableOpacity
            style={[styles.optionRow, { backgroundColor: surface, borderColor: border }]}
            activeOpacity={0.65}
            onPress={() =>
              confirmAccountAction(
                'Deactivate account',
                'Your account will be blocked until reactivated.',
                'Deactivate',
                () => deactivateMutation.mutateAsync(),
              )
            }
          >
            <View style={styles.optionLeft}>
              <Text style={styles.optionEmoji}>⏸</Text>
              <Text style={[styles.optionLabel, { color: text }]}>Deactivate Account</Text>
            </View>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.optionRow, { backgroundColor: surface, borderColor: border, marginTop: spacing.sm }]}
            activeOpacity={0.65}
            onPress={() =>
              confirmAccountAction(
                'Delete account',
                'This permanently removes your account and application records.',
                'Delete',
                () => deleteMutation.mutateAsync(),
              )
            }
          >
            <View style={styles.optionLeft}>
              <Text style={styles.optionEmoji}>⌫</Text>
              <Text style={[styles.optionLabel, { color: colors.danger }]}>Delete My Account</Text>
            </View>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.optionRow, { backgroundColor: surface, borderColor: border, marginTop: spacing.sm }]}
            activeOpacity={0.65}
            onPress={() => signOut().then(() => router.replace('/login'))}
          >
            <View style={styles.optionLeft}>
              <Text style={styles.optionEmoji}>🚪</Text>
              <Text style={[styles.optionLabel, { color: colors.danger }]}>Log Out</Text>
            </View>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  scrollContent: { paddingBottom: 40 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  backBtn: {
    width: 38,
    height: 38,
    borderRadius: radius.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backArrow: {
    fontSize: 26,
    fontWeight: '600',
    lineHeight: 30,
  },
  title: {
    fontSize: typography.fontSize.title,
    fontWeight: '800',
    letterSpacing: typography.letterSpacing.tight,
    flex: 1,
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
  userDetail: {
    fontSize: typography.fontSize.bodySmall,
    marginTop: 2,
  },
  statusChip: {
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.full,
  },
  statusText: {
    fontSize: typography.fontSize.micro,
    fontWeight: '800',
    letterSpacing: typography.letterSpacing.wider,
    color: colors.accentDark,
  },
  sectionLabel: {
    fontSize: typography.fontSize.caption,
    fontWeight: '700',
    letterSpacing: typography.letterSpacing.wider,
    textTransform: 'uppercase',
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
    paddingHorizontal: spacing.lg,
  },
  optionsList: {
    paddingHorizontal: spacing.lg,
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
});