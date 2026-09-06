export { colors } from './colors';
export type { ColorKey } from './colors';

export const typography = {
  fontFamily: {
    regular: 'System',
    medium: 'System',
    semiBold: 'System',
    bold: 'System',
  },
  fontSize: {
    display: 34,
    title: 28,
    heading: 22,
    subheading: 18,
    body: 16,
    bodySmall: 14,
    caption: 12,
    micro: 10,
  },
  lineHeight: {
    display: 42,
    title: 36,
    heading: 30,
    subheading: 26,
    body: 24,
    bodySmall: 20,
    caption: 16,
    micro: 14,
  },
  letterSpacing: {
    tight: -0.5,
    normal: 0,
    wide: 0.5,
    wider: 1,
    widest: 2,
  },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
} as const;

export const radius = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  full: 999,
} as const;

export const shadows = {
  none: {
    shadowColor: 'transparent',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
  soft: {
    shadowColor: '#0D0B1A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 2,
  },
  card: {
    shadowColor: '#0D0B1A',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 3,
  },
  elevated: {
    shadowColor: '#0D0B1A',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.10,
    shadowRadius: 24,
    elevation: 6,
  },
  accent: {
    shadowColor: '#C9A96A',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 16,
    elevation: 8,
  },
} as const;

export const layout = {
  screenPaddingHorizontal: 24,
  cardPadding: 16,
  sectionGap: 32,
  itemGap: 16,
  bottomNavHeight: 80,
  headerHeight: 56,
} as const;
