import React from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, useColorScheme, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNotificationsQuery } from '../src/hooks/queries';
import { useMarkAllNotificationsReadMutation, useMarkNotificationReadMutation } from '../src/hooks/mutations';
import { parseApiError } from '../src/api/errors';
import { EmptyState } from '../src/components/Core';
import { colors, radius, spacing, typography } from '../src/theme';

export default function NotificationsScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';
  const notificationsQuery = useNotificationsQuery();
  const readMutation = useMarkNotificationReadMutation();
  const readAllMutation = useMarkAllNotificationsReadMutation();
  const items = notificationsQuery.data ?? [];

  const bg = dark ? colors.darkBackground : colors.background;
  const surface = dark ? colors.darkSurface : colors.surface;
  const border = dark ? colors.darkBorder : colors.border;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
          <Text style={[styles.backArrow, { color: text }]}>‹</Text>
        </TouchableOpacity>
        <Text style={[styles.title, { color: text }]}>Notifications</Text>
        {items.length > 0 ? (
          <TouchableOpacity onPress={() => readAllMutation.mutate()} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
            <Text style={styles.action}>Mark all read</Text>
          </TouchableOpacity>
        ) : (
          <View style={{ width: 78 }} />
        )}
      </View>

      {notificationsQuery.isLoading ? (
        <View style={styles.state}>
          <Text style={{ color: secondary }}>Loading notifications…</Text>
        </View>
      ) : notificationsQuery.isError ? (
        <View style={styles.state}>
          <Text style={[styles.errorText, { color: colors.danger }]}>{parseApiError(notificationsQuery.error).message}</Text>
          <TouchableOpacity style={[styles.retryCta, { backgroundColor: colors.accent }]} activeOpacity={0.85} onPress={() => notificationsQuery.refetch()}>
            <Text style={styles.retryCtaText}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : items.length === 0 ? (
        <ScrollView contentContainerStyle={styles.emptyWrap}>
          <EmptyState
            emoji="🔔"
            title="No notifications yet"
            subtitle="When something happens with your try-ons or account, you'll see it here."
          />
        </ScrollView>
      ) : (
        <ScrollView
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
        >
          {items.map((item) => (
            <TouchableOpacity
              key={item.id}
              style={[
                styles.item,
                { backgroundColor: surface, borderColor: !item.is_read ? colors.accent : border },
              ]}
              activeOpacity={0.7}
              onPress={() => readMutation.mutate(item.id)}
            >
              <View style={styles.itemTop}>
                <Text style={[styles.itemTitle, { color: text }]}>{item.title}</Text>
                {!item.is_read ? <View style={styles.unreadDot} /> : null}
              </View>
              <Text style={[styles.itemMessage, { color: secondary }]}>{item.message}</Text>
              <Text style={[styles.itemDate, { color: secondary }]}>
                {new Date(item.created_at).toLocaleString()}
              </Text>
            </TouchableOpacity>
          ))}
          <View style={{ height: spacing.xl }} />
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
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
  action: {
    color: colors.accent,
    fontWeight: '700',
    fontSize: typography.fontSize.bodySmall,
  },
  state: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
  },
  errorText: {
    fontSize: typography.fontSize.bodySmall,
    textAlign: 'center',
    lineHeight: typography.lineHeight.bodySmall,
  },
  retryCta: {
    marginTop: spacing.lg,
    paddingHorizontal: spacing.xl,
    paddingVertical: 12,
    borderRadius: radius.full,
  },
  retryCtaText: {
    color: colors.primary,
    fontWeight: '700',
    fontSize: typography.fontSize.body,
  },
  emptyWrap: {
    paddingTop: spacing.xxxl,
  },
  list: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  item: {
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  itemTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  itemTitle: {
    fontWeight: '800',
    flexShrink: 1,
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: radius.full,
    backgroundColor: colors.accent,
  },
  itemMessage: {
    marginTop: 4,
    fontSize: typography.fontSize.bodySmall,
    lineHeight: typography.lineHeight.bodySmall,
  },
  itemDate: {
    fontSize: typography.fontSize.caption,
    marginTop: spacing.sm,
  },
});