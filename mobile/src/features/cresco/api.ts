import type { ZodType } from 'zod';
import { baseUrl, serverStore } from '@/api/config';
import { tokenStore } from '@/api/session';
import {
  CrescoApiError,
  type CrescoErrorCode,
} from './model';
import { getCrescoSessionToken } from './session';

export type CrescoRequest = {
  method?: 'GET' | 'POST';
  path: string;
  query?: Record<string, string | number | undefined>;
  body?: unknown;
  signal?: AbortSignal;
};

function buildUrl(activeBaseUrl: string, request: CrescoRequest): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(request.query ?? {})) {
    if (value !== undefined && value !== '') query.set(key, String(value));
  }
  const encoded = query.toString();
  return activeBaseUrl + request.path + (encoded ? '?' + encoded : '');
}

function mapErrorCode(status: number, rawCode?: string): CrescoErrorCode {
  if (
    rawCode === 'missing_api_key' ||
    rawCode === 'invalid_api_key' ||
    rawCode === 'model_unavailable' ||
    rawCode === 'quota_exceeded' ||
    rawCode === 'timeout' ||
    rawCode === 'upstream_error'
  ) {
    return rawCode;
  }
  if (status === 401 || status === 403) return 'invalid_api_key';
  if (status === 404) return 'model_unavailable';
  if (status === 429) return 'quota_exceeded';
  if (status === 504) return 'timeout';
  if (status === 400) return 'missing_api_key';
  return 'upstream_error';
}

/**
 * Dedicated HTTP helper for Cresco endpoints.
 * - Attaches Authorization Bearer (if logged in) and X-Cresco-Session (in-memory only).
 * - Never triggers AgroShift logout on Gemini 401 invalid_api_key errors.
 * - Parses { error, error_code } from backend responses.
 */
export async function crescoRequestJson<T>(request: CrescoRequest, schema: ZodType<T>): Promise<T> {
  const activeBaseUrl = serverStore ? await serverStore.get() : baseUrl;
  if (!activeBaseUrl || !/^https?:\/\//i.test(activeBaseUrl)) {
    throw new CrescoApiError('configuration');
  }

  const authToken = await tokenStore.get().catch(() => null);
  const crescoToken = getCrescoSessionToken();
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (authToken) headers.Authorization = 'Bearer ' + authToken;
  if (crescoToken) headers['X-Cresco-Session'] = crescoToken;
  if (request.body !== undefined) headers['Content-Type'] = 'application/json';

  let response: Response;
  try {
    response = await fetch(buildUrl(activeBaseUrl, request), {
      method: request.method ?? 'GET',
      headers,
      signal: request.signal,
      body: request.body === undefined ? undefined : JSON.stringify(request.body),
    });
  } catch (cause) {
    if (request.signal?.aborted) throw cause;
    throw new CrescoApiError('network', undefined, undefined, { cause });
  }

  const json: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const obj = json && typeof json === 'object' ? (json as Record<string, unknown>) : null;
    const rawCode = typeof obj?.error_code === 'string'
      ? obj.error_code
      : typeof obj?.code === 'string'
        ? obj.code
        : undefined;
    const message = typeof obj?.error === 'string' ? obj.error : undefined;
    throw new CrescoApiError(mapErrorCode(response.status, rawCode), response.status, message);
  }

  const parsed = schema.safeParse(json);
  if (!parsed.success) {
    throw new CrescoApiError('invalid-response', response.status, undefined, { cause: parsed.error });
  }
  return parsed.data;
}
