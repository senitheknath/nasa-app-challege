import { Manrope_400Regular } from '@expo-google-fonts/manrope/400Regular';
import { Manrope_500Medium } from '@expo-google-fonts/manrope/500Medium';
import { Manrope_600SemiBold } from '@expo-google-fonts/manrope/600SemiBold';
import { Manrope_700Bold } from '@expo-google-fonts/manrope/700Bold';
import { Manrope_800ExtraBold } from '@expo-google-fonts/manrope/800ExtraBold';
import type { TextStyle } from 'react-native';

export const fonts = {
  Manrope_400Regular, Manrope_500Medium, Manrope_600SemiBold, Manrope_700Bold, Manrope_800ExtraBold,
};

export const typography = {
  hero: { fontFamily: 'Manrope_800ExtraBold', fontSize: 34, lineHeight: 37 },
  title: { fontFamily: 'Manrope_700Bold', fontSize: 22, lineHeight: 25 },
  heading: { fontFamily: 'Manrope_700Bold', fontSize: 24, lineHeight: 29 },
  cardTitle: { fontFamily: 'Manrope_700Bold', fontSize: 20, lineHeight: 25 },
  strategy: { fontFamily: 'Manrope_700Bold', fontSize: 22, lineHeight: 28 },
  action: { fontFamily: 'Manrope_700Bold', fontSize: 18, lineHeight: 24 },
  body: { fontFamily: 'Manrope_400Regular', fontSize: 14, lineHeight: 20 },
  input: { fontFamily: 'Manrope_500Medium', fontSize: 15, lineHeight: 21 },
  button: { fontFamily: 'Manrope_700Bold', fontSize: 15, lineHeight: 20 },
  value: { fontFamily: 'Manrope_800ExtraBold', fontSize: 24, lineHeight: 29 },
  metric: { fontFamily: 'Manrope_800ExtraBold', fontSize: 28, lineHeight: 31 },
  unit: { fontFamily: 'Manrope_600SemiBold', fontSize: 16, lineHeight: 22 },
  detail: { fontFamily: 'Manrope_400Regular', fontSize: 13, lineHeight: 18 },
  chip: { fontFamily: 'Manrope_600SemiBold', fontSize: 13, lineHeight: 18 },
  caption: { fontFamily: 'Manrope_500Medium', fontSize: 12, lineHeight: 16 },
  badge: { fontFamily: 'Manrope_600SemiBold', fontSize: 12, lineHeight: 16 },
  label: { fontFamily: 'Manrope_500Medium', fontSize: 11, lineHeight: 15 },
  tag: { fontFamily: 'Manrope_600SemiBold', fontSize: 11, lineHeight: 15, letterSpacing: .88, textTransform: 'uppercase' },
  smallBold: { fontFamily: 'Manrope_700Bold', fontSize: 11, lineHeight: 15 },
  brand: { fontFamily: 'Manrope_800ExtraBold', fontSize: 15, lineHeight: 16, letterSpacing: 1.8 },
  brandSub: { fontFamily: 'Manrope_600SemiBold', fontSize: 9, lineHeight: 12, letterSpacing: 1.44, textTransform: 'uppercase' },
} satisfies Record<string, TextStyle>;
