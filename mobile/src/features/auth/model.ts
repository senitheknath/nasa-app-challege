import { z } from 'zod';

export const authUserSchema = z.object({
  id: z.number().int(),
  email: z.string().email(),
  display_name: z.string().nullable().optional(),
});

export const authResponseSchema = z.object({
  token: z.string().min(1),
  user: authUserSchema,
});

export const geoPointSchema = z.object({
  latitude: z.number(),
  longitude: z.number(),
});

export const savedFarmSchema = z.object({
  id: z.number().int(),
  name: z.string().min(1),
  country: z.string().min(1),
  latitude: z.number(),
  longitude: z.number(),
  area_ha: z.number().nullable().optional(),
  boundary: z.unknown().nullable().optional(),
  irrigation: z.string().nullable().optional(),
  crop_id: z.string().nullable().optional(),
  start_date: z.string().nullable().optional(),
  farm: z.record(z.string(), z.unknown()).nullable().optional(),
  updated_at: z.string().optional(),
});

export type AuthUserDto = z.infer<typeof authUserSchema>;
export type SavedFarm = z.infer<typeof savedFarmSchema>;
