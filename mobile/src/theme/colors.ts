export const colors = {
  // Brand
  primary: '#0D0B1A', // Deep Navy / Near Black
  primaryLight: '#1B1730',
  primaryMid: '#2A2545',
  accent: '#C9A96A', // Sophisticated Gold / Champagne
  accentDark: '#B08D4F',
  accentSoft: '#F4EBDD',
  accentGlow: 'rgba(201,169,106,0.15)',
  mutedPurple: '#8A7BA8',
  mutedPurpleSoft: '#E8E4F0',

  // Neutrals
  background: '#FAF8F5', // Warm White / Off White
  surface: '#FFFFFF',
  surfaceAlt: '#F3F0EA',
  surfaceHover: '#EDE9E1',
  border: '#EAE6DE',
  borderLight: '#F0EDE6',
  divider: '#E5E1D9',

  // Text
  textPrimary: '#14101F',
  textSecondary: '#6E6A76',
  textMuted: '#9A96A1',
  textOnDark: '#FFFFFF',
  textOnDarkMuted: '#B9B4C2',
  textLink: '#C9A96A',

  // System
  success: '#2E7D5B',
  successSoft: '#E4F1EA',
  danger: '#C0392B',
  dangerSoft: '#F9E9E7',
  warning: '#B8860B',
  warningSoft: '#FFF8E7',
  info: '#3B82F6',
  infoSoft: '#EFF6FF',

  // Dark mode
  darkBackground: '#12101B',
  darkSurface: '#1B1826',
  darkSurfaceAlt: '#221E30',
  darkSurfaceHover: '#2A2540',
  darkBorder: '#2C2740',
  darkBorderLight: '#352F4A',
  darkTextPrimary: '#F4F2F7',
  darkTextSecondary: '#A9A4B4',
  darkTextMuted: '#6E6A76',
} as const;

export type ColorKey = keyof typeof colors;
