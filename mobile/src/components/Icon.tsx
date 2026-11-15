import Svg, { Path } from 'react-native-svg';
import { colors, icons } from '@/theme/tokens';

const paths = {
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM21 21l-4.3-4.3',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  diagonal: 'M7 17 17 7M8 7h9v9',
  back: 'M19 12H5M11 18l-6-6 6-6',
  check: 'M5 12.5l4.5 4.5L19 7',
  trash: 'M4 7h16M10 11v6M14 11v6M6 7l1 12h10l1-12M9 7V4h6v3',
  layers: 'M12 3 3 8l9 5 9-5-9-5ZM3 13l9 5 9-5',
  drop: 'M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z',
  calendar: 'M4 6h16v14H4zM4 10h16M8 3v4M16 3v4',
  sprout: 'M12 21v-9M12 12c0-4-2.5-6-7-6 0 4 2.5 6 7 6ZM12 14c0-3.5 2.2-5.5 7-5.5 0 3.5-2.2 5.5-7 5.5Z',
  pin: 'M12 21s7-6 7-11a7 7 0 0 0-14 0c0 5 7 11 7 11ZM12 12a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',
  redo: 'M20 12a8 8 0 1 1-2.4-5.7M20 4v4h-4',
  map: 'M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2ZM9 4v14M15 6v14',
  globe: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18',
  user: 'M20 21a8 8 0 0 0-16 0M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z',
  bookmark: 'M6 4h12a1 1 0 0 1 1 1v16l-7-4-7 4V5a1 1 0 0 1 1-1Z',
  cube: 'M12 2 3 7v10l9 5 9-5V7l-9-5ZM3 7l9 5 9-5M12 12v10',
  activity: 'M3 12h4l3-8 4 16 3-8h4',
  plus: 'M12 5v14M5 12h14',
} as const;

export type IconName = keyof typeof paths;

export function Icon({ name, color = colors.cream, size = icons.regular }: { name: IconName; color?: string; size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" aria-hidden>
      <Path d={paths[name]} fill="none" stroke={color} strokeWidth={icons.stroke} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}
