export const useMocks = process.env.EXPO_PUBLIC_USE_MOCKS !== 'false';
export const baseUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.trim().replace(/\/+$/, '');
