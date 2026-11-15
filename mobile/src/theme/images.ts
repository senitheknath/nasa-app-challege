import type { ImageSource } from 'expo-image';

export type Picture = ImageSource | number;
export const pictures = {
  hero: require('../../assets/cresco/hero.jpg') as number,
  aerial: require('../../assets/cresco/aerial.jpg') as number,
  field: require('../../assets/cresco/field.jpg') as number,
} satisfies Record<string, Picture>;
