export const colors = {
  forest950: '#12170C',
  forest900: '#1B2211',
  forest800: '#2A3419',
  forest700: '#3D4B25',
  accent: '#C8F31D',
  cream: '#F1F4E6',
  sage: '#B5C19B',
  danger: '#FF8A7A',
  transparent: 'transparent',
  glass: 'rgba(42,52,25,.42)',
  strongGlass: 'rgba(22,28,13,.62)',
  opaqueGlass: 'rgba(30,38,18,.92)',
  card: 'rgba(42,52,25,.58)',
  selectedCard: 'rgba(27,34,17,.8)',
  iconGlass: 'rgba(27,34,17,.6)',
  iconDark: 'rgba(18,23,12,.8)',
  innerDark: 'rgba(18,23,12,.6)',
  border: 'rgba(255,255,255,.10)',
  glassBorder: 'rgba(255,255,255,.14)',
  strongBorder: 'rgba(255,255,255,.12)',
  chip: 'rgba(255,255,255,.10)',
  reached: 'rgba(255,255,255,.05)',
  segment: 'rgba(255,255,255,.20)',
  handle: 'rgba(255,255,255,.30)',
  muted: 'rgba(241,244,230,.50)',
  secondary: 'rgba(241,244,230,.80)',
  locked: 'rgba(181,193,155,.40)',
  highlight: 'rgba(200,243,29,.10)',
  accentBorder: 'rgba(200,243,29,.40)',
  focus: 'rgba(200,243,29,.70)',
  parcel: 'rgba(200,243,29,.16)',
  dangerFill: 'rgba(255,138,122,.15)',
  dangerBorder: 'rgba(255,138,122,.50)',
  shadow: '#080C04',
  skeleton: 'rgba(255,255,255,.11)',
  grid: 'rgba(255,255,255,.088)',
  topScrim: 'rgba(18,23,12,.80)',
  middleScrim: 'rgba(18,23,12,.40)',
  bottomScrim: 'rgba(18,23,12,.90)',
  imageTint: 'rgba(18,23,12,.70)',
  aerialTint: 'rgba(50,63,30,.23)',
  heroScrim: ['rgba(18,23,12,.70)', 'rgba(18,23,12,.35)', 'rgba(18,23,12,.90)'],
  mapScrim: ['rgba(18,23,12,.60)', 'transparent', 'rgba(18,23,12,.80)'],
  parcelScrim: ['rgba(18,23,12,.70)', 'transparent', 'rgba(18,23,12,.50)'],
} as const;

export const space = {
  xxs: 2, xs: 4, tight: 6, sm: 8, snug: 10, md: 12, tile: 14, lg: 16,
  gutter: 20, xl: 24, xxl: 32, fade: 40,
} as const;

export const radius = { tile: 24, card: 28, sheet: 32, pill: 999 } as const;
export const size = {
  hairline: 1, outline: 2, indicator: 6, dot: 8, vertex: 14, activeVertex: 20,
  touch: 44, control: 48, primary: 56, workflow: 72, searchResults: 224,
  grid: 52, roomyCanvas: 700, webTop: 56, navigation: 176, keyboardClearance: 20,
  planPeek: 230, dateField: 48, maxContent: 600, planHero: '60%', planSheet: '70%',
  parcelHeight: '34%', parcelTop: '12%', skeletonList: 112, skeletonAction: 96,
  skeletonLine: 64, skeletonMap: 160, sheetHandleWidth: 44,
} as const;
export const icons = { grid: 24, small: 16, regular: 20, badge: 12, stroke: 1.5 } as const;
export const motion = { enter: 450, progress: 700, shimmer: 600, search: 150, pressScale: .96, disabledOpacity: .45, rise: 14 } as const;
export const glass = {
  blur: 18, strongBlur: 22, saturation: 130,
  shadow: { shadowColor: colors.shadow, shadowOffset: { width: 0, height: 8 }, shadowOpacity: .28, shadowRadius: 16 },
  actionShadow: { shadowColor: colors.accent, shadowOffset: { width: 0, height: 8 }, shadowOpacity: .28, shadowRadius: 14 },
} as const;
export const wireframe = { bounds: 100, padding: 12, stroke: 1.6, fanStroke: 1, dash: '5 4', fanOpacity: .55 } as const;
