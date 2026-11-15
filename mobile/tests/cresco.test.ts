import { expireSession, tokenStore } from '@/api/session';
import { crescoRequestJson } from '@/features/cresco/api';
import {
  findClearBubblePosition,
  overlapArea,
  useAvoidanceStore,
  type AvoidanceRect,
  type BubbleBounds,
} from '@/features/cresco/avoidance';
import {
  CrescoApiError,
  crescoChatResponseSchema,
  crescoConnectResponseSchema,
  crescoStatusResponseSchema,
  formatCrescoError,
} from '@/features/cresco/model';
import {
  clearCrescoSessionToken,
  getCrescoSessionToken,
  setCrescoSessionToken,
} from '@/features/cresco/session';

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

describe('Cresco mobile session & API layer', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    clearCrescoSessionToken();
    jest.restoreAllMocks();
  });

  afterAll(() => {
    global.fetch = originalFetch;
  });

  it('stores Cresco session token in memory only and clears on AgroShift session expiry', async () => {
    expect(getCrescoSessionToken()).toBeNull();
    setCrescoSessionToken('  tok-abc-123  ');
    expect(getCrescoSessionToken()).toBe('tok-abc-123');

    await expireSession(null);
    expect(getCrescoSessionToken()).toBeNull();

    setCrescoSessionToken('tok-xyz');
    clearCrescoSessionToken();
    expect(getCrescoSessionToken()).toBeNull();
  });

  it('attaches X-Cresco-Session & Bearer headers and does not log out AgroShift on Gemini 401', async () => {
    jest.spyOn(tokenStore, 'get').mockResolvedValue('agroshift-jwt');
    setCrescoSessionToken('cresco-sess-1');

    const mockFetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({
        connected: false,
        error: 'Invalid or unauthorized Gemini API key.',
        error_code: 'invalid_api_key',
      }),
    });
    global.fetch = mockFetch as unknown as typeof fetch;

    await expect(
      crescoRequestJson(
        { method: 'POST', path: '/api/cresco/connect', body: { api_key: 'bad-key' } },
        crescoConnectResponseSchema,
      ),
    ).rejects.toMatchObject({
      name: 'CrescoApiError',
      code: 'invalid_api_key',
      status: 401,
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer agroshift-jwt');
    expect(headers['X-Cresco-Session']).toBe('cresco-sess-1');
  });

  it('parses valid connect, status, and chat responses with Zod schemas', () => {
    const conn = crescoConnectResponseSchema.parse({
      connected: true,
      model: 'gemini-3.8-flash',
      session_token: 'sess-1',
      expires_at: '2026-11-15T23:00:00Z',
      ttl_seconds: 3600,
    });
    expect(conn.connected).toBe(true);
    expect(conn.model).toBe('gemini-3.8-flash');

    const status = crescoStatusResponseSchema.parse({
      connected: true,
      model: 'gemini-3.8-flash',
      history_count: 2,
      history: [
        { role: 'user', content: 'Which crop?' },
        { role: 'assistant', content: 'Mungbean fits well.' },
      ],
    });
    expect(status.history).toHaveLength(2);

    const chat = crescoChatResponseSchema.parse({
      reply: 'Plant mungbean.',
      model: 'gemini-3.8-flash',
      farm_id: 'farm-1',
      language: 'en',
      history_count: 2,
    });
    expect(chat.reply).toBe('Plant mungbean.');
  });

  it('formats Gemini and network errors clearly for users', () => {
    expect(formatCrescoError(new CrescoApiError('invalid_api_key', 401))).toContain('Invalid Gemini API key');
    expect(formatCrescoError(new CrescoApiError('model_unavailable', 404))).toContain('gemini-flash-lite-latest');
    expect(formatCrescoError(new CrescoApiError('quota_exceeded', 429))).toContain('quota');
    expect(formatCrescoError(new CrescoApiError('timeout', 504))).toContain('timed out');
    expect(formatCrescoError(new CrescoApiError('network'))).toContain('Network error');
  });
});

describe('CrescoBubble avoidance solver', () => {
  const bounds: BubbleBounds = { minX: 14, maxX: 320, minY: 60, maxY: 740 };
  const bubbleSize = 56;

  beforeEach(() => {
    useAvoidanceStore.setState({ zones: {} });
  });

  it('snaps to nearest screen edge when no buttons or texts overlap', () => {
    const pos = findClearBubblePosition({ x: 260, y: 400 }, bubbleSize, bounds, {}, true);
    expect(pos).toEqual({ x: 320, y: 400 });

    const leftPos = findClearBubblePosition({ x: 80, y: 400 }, bubbleSize, bounds, {}, true);
    expect(leftPos).toEqual({ x: 14, y: 400 });
  });

  it('intentionally moves away from a button or text blocking the target edge', () => {
    const zones: Record<string, AvoidanceRect> = {
      'primary-btn': { x: 200, y: 390, width: 170, height: 54, padding: 10, kind: 'button' },
      'header-text': { x: 16, y: 48, width: 350, height: 64, padding: 12, kind: 'chrome' },
    };

    const resolved = findClearBubblePosition({ x: 320, y: 400 }, bubbleSize, bounds, zones, true);
    expect(overlapArea(resolved, bubbleSize, Object.values(zones))).toBe(0);
    // Should dodge above or below the button rather than sitting on top of it
    expect(resolved.y <= 390 - 10 - bubbleSize || resolved.y >= 390 + 54 + 10).toBe(true);
  });

  it('switches to the opposite edge when the entire preferred edge is occupied', () => {
    const zones: Record<string, AvoidanceRect> = {
      'right-rail': { x: 290, y: 50, width: 90, height: 720, padding: 10, kind: 'button' },
    };

    const resolved = findClearBubblePosition({ x: 320, y: 350 }, bubbleSize, bounds, zones, true);
    expect(resolved.x).toBe(bounds.minX);
    expect(overlapArea(resolved, bubbleSize, Object.values(zones))).toBe(0);
  });

  it('registers and unregisters avoidance zones in the store', () => {
    const store = useAvoidanceStore.getState();
    store.registerZone('btn-1', { x: 20, y: 100, width: 120, height: 48, kind: 'button' });
    expect(useAvoidanceStore.getState().zones['btn-1']).toBeDefined();
    store.unregisterZone('btn-1');
    expect(useAvoidanceStore.getState().zones['btn-1']).toBeUndefined();
  });
});
