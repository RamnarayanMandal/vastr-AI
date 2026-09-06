import React from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, useColorScheme, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { SUPPORT } from '../src/constants/support';
import { colors, radius, spacing, typography } from '../src/theme';

const sections = [
  ['Information we collect', 'VastrAI stores account details such as your name, email, mobile number, and password hash. When you use try-on, we receive the person and fabric images you upload and the generated try-on image.'],
  ['How information is used', 'Account information supports authentication and account management. Images are used to run the selected AI try-on workflow, store results, and show your history.'],
  ['Storage and processing', 'Uploaded and generated images are stored using the configured ImageKit storage service. The backend downloads images for processing and sends required image data to the configured AI provider.'],
  ['Third-party services', 'ImageKit provides image storage and delivery. The configured AI provider processes images to generate the try-on result. Their handling is governed by their own terms and policies.'],
  ['Retention and deletion', 'Try-on jobs, results, and account records remain until you delete your account or an administrator applies a retention policy. Account deletion removes the associated application records; external storage cleanup depends on the configured storage integration.'],
  ['Security and questions', `The service uses authenticated API access and password hashing. No online service can promise absolute security. Privacy questions can be sent to ${SUPPORT.email}.`],
];

export default function PrivacyScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const scheme = useColorScheme();
  const dark = scheme === 'dark';

  const bg = dark ? colors.darkBackground : colors.background;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const secondary = dark ? colors.darkTextSecondary : colors.textSecondary;

  return (
    <View style={[styles.screen, { backgroundColor: bg }]}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
          <Text style={[styles.backArrow, { color: text }]}>‹</Text>
        </TouchableOpacity>
        <Text style={[styles.title, { color: text }]}>Privacy Policy</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={[styles.updated, { color: secondary }]}>
          Information about this application and its current services.
        </Text>
        {sections.map(([heading, body]) => (
          <View key={heading} style={styles.section}>
            <Text style={[styles.heading, { color: text }]}>{heading}</Text>
            <Text style={[styles.body, { color: secondary }]}>{body}</Text>
          </View>
        ))}
        <View style={{ height: spacing.xl }} />
      </ScrollView>
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
  content: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  updated: {
    marginBottom: spacing.sm,
    fontSize: typography.fontSize.bodySmall,
    lineHeight: typography.lineHeight.bodySmall,
  },
  section: {
    marginTop: spacing.lg,
  },
  heading: {
    fontSize: typography.fontSize.subheading,
    fontWeight: '800',
  },
  body: {
    fontSize: typography.fontSize.bodySmall,
    lineHeight: typography.lineHeight.bodySmall,
    marginTop: spacing.sm,
  },
});