import React, { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing, typography } from '../theme';

interface ProgressBarProps {
  percent: number;
  label?: string;
  dark: boolean;
  /** When true, show an indeterminate sweep with NO numeric percentage. */
  indeterminate?: boolean;
}

/** Horizontal progress bar. Numeric mode shows a real percentage; indeterminate
 *  mode animates a sweep without showing any (potentially fake) number. */
export default function ProgressBar({ percent, label, dark, indeterminate }: ProgressBarProps) {
  const sweep = useRef(new Animated.Value(0)).current;
  const track = dark ? colors.darkBorder : colors.border;
  const text = dark ? colors.darkTextPrimary : colors.textPrimary;
  const sub = dark ? colors.darkTextSecondary : colors.textSecondary;

  useEffect(() => {
    if (!indeterminate) return;
    const loop = Animated.loop(
      Animated.timing(sweep, {
        toValue: 1,
        duration: 1600,
        easing: Easing.inOut(Easing.ease),
        useNativeDriver: true,
      })
    );
    loop.start();
    return () => loop.stop();
  }, [indeterminate, sweep]);

  if (indeterminate) {
    const translateX = sweep.interpolate({
      inputRange: [0, 1],
      outputRange: [-160, 340],
    });
    return (
      <View style={styles.wrap}>
        {label && (
          <View style={styles.header}>
            <Text style={[styles.label, { color: sub }]}>{label}</Text>
          </View>
        )}
        <View style={[styles.track, { backgroundColor: track }]}>
          <Animated.View
            style={[
              styles.indetFill,
              { transform: [{ translateX }] },
            ]}
          />
        </View>
      </View>
    );
  }

  const pct = Math.min(100, Math.max(0, Math.round(percent)));
  return (
    <View style={styles.wrap}>
      {(label || pct >= 0) && (
        <View style={styles.header}>
          <Text style={[styles.label, { color: sub }]}>{label ?? 'Generating'}</Text>
          <Text style={[styles.percent, { color: text }]}>{pct}%</Text>
        </View>
      )}
      <View style={[styles.track, { backgroundColor: track }]}>
        <View style={[styles.fill, { width: `${pct}%`, backgroundColor: colors.accent }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: '100%',
    gap: spacing.xs,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  label: {
    fontSize: typography.fontSize.bodySmall,
    fontWeight: '600',
  },
  percent: {
    fontSize: typography.fontSize.body,
    fontWeight: '800',
    fontVariant: ['tabular-nums'],
  },
  track: {
    width: '100%',
    height: 8,
    borderRadius: radius.full,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: radius.full,
  },
  indetFill: {
    position: 'absolute',
    width: 120,
    borderRadius: radius.full,
    backgroundColor: colors.accent,
    height: '100%',
  },
});
