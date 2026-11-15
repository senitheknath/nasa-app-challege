import { z } from 'zod';
import { requestJson } from '@/api/client';
import { onSessionExpired, tokenStore } from '@/api/session';

jest.mock('@/api/config', () => ({ useMocks: false, baseUrl: 'https://api.example.test' }));
jest.mock('expo-secure-store', () => {
  let value: string | null = null;
  return {
    getItemAsync: jest.fn(async () => value),
    setItemAsync: jest.fn(async (_key: string, next: string) => { value = next; }),
    deleteItemAsync: jest.fn(async () => { value = null; }),
  };
});

const schema = z.object({ id: z.string() });
const request = { path: '/v1/test', query: { q: 'rice & beans', cursor: undefined } };

function reply(status: number, body: unknown) {
  return { status, ok: status >= 200 && status < 300, json: async () => body } as Response;
}

beforeEach(async () => { await tokenStore.clear(); });
afterEach(() => jest.restoreAllMocks());

test('adds the bearer header and encodes query parameters', async () => {
  await tokenStore.set('current-token');
  const fetch = jest.spyOn(globalThis, 'fetch').mockResolvedValue(reply(200, { id: 'rice' }));
  await expect(requestJson(request, schema)).resolves.toEqual({ id: 'rice' });
  expect(fetch).toHaveBeenCalledWith('https://api.example.test/v1/test?q=rice+%26+beans',
    expect.objectContaining({ headers: { Accept: 'application/json', Authorization: 'Bearer current-token' } }));
});

test('clears the rejected session and normalizes a 401', async () => {
  const expired = jest.fn();
  const dispose = onSessionExpired(expired);
  try {
    await tokenStore.set('expired');
    jest.spyOn(globalThis, 'fetch').mockResolvedValue(reply(401, { code: 'EXPIRED' }));
    await expect(requestJson(request, schema)).rejects.toMatchObject({ kind: 'http', status: 401, code: 'EXPIRED' });
    expect(expired).toHaveBeenCalledTimes(1);
    await expect(tokenStore.get()).resolves.toBeNull();
  } finally {
    dispose();
  }
});

test('retains a new token when a previous request returns 401', async () => {
  await tokenStore.set('previous');
  jest.spyOn(globalThis, 'fetch').mockImplementation(async () => {
    await tokenStore.set('new');
    return reply(401, { code: 'EXPIRED' });
  });
  await expect(requestJson(request, schema)).rejects.toMatchObject({ status: 401 });
  await expect(tokenStore.get()).resolves.toBe('new');
});

test('rejects malformed JSON shapes and normalizes a network failure', async () => {
  const fetch = jest.spyOn(globalThis, 'fetch').mockResolvedValueOnce(reply(200, { id: 42 }))
    .mockRejectedValueOnce(new TypeError('Connection failed'));
  await expect(requestJson(request, schema)).rejects.toMatchObject({ kind: 'invalid-response' });
  await expect(requestJson(request, schema)).rejects.toMatchObject({ kind: 'network' });
  expect(fetch).toHaveBeenCalledTimes(2);
});
