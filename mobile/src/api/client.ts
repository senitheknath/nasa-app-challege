import type { ZodType } from 'zod';
import { baseUrl } from './config';
import { ApiError } from './errors';
import { expireSession, tokenStore } from './session';

export type Request = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  path: string;
  query?: Record<string, string | number | undefined>;
  body?: unknown;
  signal?: AbortSignal;
};

function endpoint(request: Request) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(request.query ?? {})) {
    if (value !== undefined) query.set(key, String(value));
  }
  const encoded = query.toString();
  return request.path + (encoded ? '?' + encoded : '');
}

async function http(request: Request): Promise<unknown> {
  if (!baseUrl || !/^https?:\/\//i.test(baseUrl)) throw new ApiError('configuration');
  const token = await tokenStore.get().catch((cause) => { throw new ApiError('configuration', undefined, undefined, { cause }); });
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (token) headers.Authorization = 'Bearer ' + token;
  if (request.body !== undefined) headers['Content-Type'] = 'application/json';

  let response: Response;
  try {
    response = await fetch(baseUrl + endpoint(request), {
      method: request.method ?? 'GET',
      headers,
      signal: request.signal,
      body: request.body === undefined ? undefined : JSON.stringify(request.body),
    });
  } catch (cause) {
    if (request.signal?.aborted) throw cause;
    throw new ApiError('network', undefined, undefined, { cause });
  }

  if (response.status === 401) await expireSession(token).catch(() => undefined);
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const code = body && typeof body === 'object' && 'code' in body && typeof body.code === 'string'
      ? body.code
      : undefined;
    const error = body && typeof body === 'object' && 'error' in body && typeof body.error === 'string'
      ? body.error
      : undefined;
    throw new ApiError('http', response.status, code ?? error);
  }
  return response.json().catch((cause) => { throw new ApiError('invalid-response', undefined, undefined, { cause }); });
}

export async function rawRequest(request: Request): Promise<unknown> {
  return http(request);
}

export async function requestJson<T>(request: Request, schema: ZodType<T>): Promise<T> {
  const data = await http(request);
  const result = schema.safeParse(data);
  if (!result.success) throw new ApiError('invalid-response', undefined, undefined, { cause: result.error });
  return result.data;
}
