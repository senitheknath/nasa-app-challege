import { z } from 'zod';

export const CRESCO_DEFAULT_MODEL = 'gemini-flash-lite-latest';
export const GOOGLE_AI_STUDIO_API_KEY_URL = 'https://aistudio.google.com/apikey';

export type CrescoErrorCode =
  | 'missing_api_key'
  | 'invalid_api_key'
  | 'model_unavailable'
  | 'quota_exceeded'
  | 'timeout'
  | 'upstream_error'
  | 'network'
  | 'configuration'
  | 'invalid-response';

export class CrescoApiError extends Error {
  constructor(
    readonly code: CrescoErrorCode,
    readonly status?: number,
    message?: string,
    options?: ErrorOptions,
  ) {
    super(message ?? code, options);
    this.name = 'CrescoApiError';
  }
}

export const crescoHistoryItemSchema = z.object({
  role: z.enum(['user', 'assistant']),
  content: z.string(),
});

export type CrescoHistoryItem = z.infer<typeof crescoHistoryItemSchema>;

export const crescoConnectResponseSchema = z.object({
  connected: z.boolean(),
  model: z.string().default(CRESCO_DEFAULT_MODEL),
  session_token: z.string(),
  expires_at: z.string().nullable().optional(),
  ttl_seconds: z.number().optional(),
});

export type CrescoConnectResponse = z.infer<typeof crescoConnectResponseSchema>;

export const crescoStatusResponseSchema = z.object({
  connected: z.boolean(),
  model: z.string().default(CRESCO_DEFAULT_MODEL),
  expires_at: z.string().nullable().optional(),
  ttl_seconds: z.number().optional(),
  history_count: z.number().optional().default(0),
  history: z.array(crescoHistoryItemSchema).optional().default([]),
});

export type CrescoStatusResponse = z.infer<typeof crescoStatusResponseSchema>;

export const crescoChatResponseSchema = z.object({
  reply: z.string(),
  model: z.string().default(CRESCO_DEFAULT_MODEL),
  farm_id: z.union([z.string(), z.number()]).nullable().optional(),
  language: z.string().optional(),
  provenance_summary: z.record(z.string(), z.unknown()).optional(),
  history_count: z.number().optional(),
});

export type CrescoChatResponse = z.infer<typeof crescoChatResponseSchema>;

export const crescoClearResponseSchema = z.object({
  cleared: z.boolean(),
  farm_id: z.union([z.string(), z.number()]).nullable().optional(),
});

export type CrescoClearResponse = z.infer<typeof crescoClearResponseSchema>;

export const crescoDisconnectResponseSchema = z.object({
  connected: z.boolean().optional(),
  disconnected: z.boolean().optional(),
});

export type CrescoDisconnectResponse = z.infer<typeof crescoDisconnectResponseSchema>;

export type CrescoInlineFarm = {
  name?: string;
  country?: string;
  latitude?: number;
  longitude?: number;
  area_ha?: number | null;
  irrigation?: string;
  crop_id?: string | null;
  sowing_date?: string;
  boundary?: { latitude: number; longitude: number }[];
};

export type CrescoChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  provenanceSummary?: Record<string, unknown>;
  language?: string;
};

export const CRESCO_STARTER_PROMPTS: readonly string[] = [
  'Which crops suit my current soil, drainage, and rainfall?',
  'Compare top 2-season rotation options for this field',
  'What are the main water and turnaround risks right now?',
  'How does my 3D soil moisture and slab profile affect sowing?',
  'Recommend a drought-resilient legume and cereal rotation',
  'Summarize NASA climate & satellite conditions for my farm',
];

export function formatCrescoError(error: unknown): string {
  if (error instanceof CrescoApiError) {
    switch (error.code) {
      case 'missing_api_key':
        return 'Please enter your Google Gemini API key.';
      case 'invalid_api_key':
        return 'Invalid Gemini API key. Check your key in Google AI Studio and try again.';
      case 'model_unavailable':
        return `The ${CRESCO_DEFAULT_MODEL} model is unavailable for this API key or region.`;
      case 'quota_exceeded':
        return 'Gemini API quota exceeded. Check your Google AI Studio usage or billing limits.';
      case 'timeout':
        return 'Gemini request timed out. Please try again.';
      case 'network':
        return 'Network error reaching the AgroShift server. Check your connection and retry.';
      case 'configuration':
        return 'AgroShift API server URL is not configured.';
      case 'invalid-response':
        return 'Received an unexpected response from Cresco AI.';
      case 'upstream_error':
        return error.message && error.message !== 'upstream_error'
          ? error.message
          : 'Gemini returned an upstream error. Please try again.';
    }
  }
  if (error instanceof Error && error.message) return error.message;
  return 'Something went wrong talking to Cresco AI.';
}
