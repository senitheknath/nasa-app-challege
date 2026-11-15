import { useReducedMotion } from 'react-native-reanimated';
import { colors, glass, icons, motion, radius, size, space, wireframe } from './tokens';
import { typography } from './typography';

export function useTheme() {
  const reducedMotion = useReducedMotion();
  return { colors, glass, icons, motion, radius, size, space, wireframe, typography, reducedMotion };
}
