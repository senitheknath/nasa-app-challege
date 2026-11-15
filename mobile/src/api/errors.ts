export type ErrorKind = 'http' | 'invalid-response' | 'network' | 'configuration';

export class ApiError extends Error {
  constructor(
    readonly kind: ErrorKind,
    readonly status?: number,
    readonly code?: string,
    options?: ErrorOptions,
  ) {
    super(code ?? kind, options);
    this.name = 'ApiError';
  }
}

export function shouldRetry(attempt: number, error: unknown) {
  if (attempt >= 2 || !(error instanceof ApiError)) return false;
  return error.kind === 'network' || error.status === 429 || (error.status !== undefined && error.status >= 500);
}
