import { z } from 'zod';

export const strategySchema = z.object({
  id: z.string().min(1), tag: z.string().min(1), title: z.string().min(1), description: z.string(), requiresCrop: z.boolean(),
});
export const strategiesSchema = z.array(strategySchema);
export type StrategyDto = z.infer<typeof strategySchema>;
export type Strategy = { id: string; tag: string; title: string; description: string; requiresCrop: boolean };
export const mapStrategy = ({ id, tag, title, description, requiresCrop }: StrategyDto): Strategy =>
  ({ id, tag, title, description, requiresCrop });

export function getSelectedStrategy(strategies: readonly Strategy[] = [], selectedId?: string | null, defaultId?: string): Strategy | undefined {
  return strategies.find((strategy) => strategy.id === selectedId)
    ?? strategies.find((strategy) => strategy.id === defaultId)
    ?? strategies.find((strategy) => strategy.id === 'continuous_rainfed')
    ?? strategies.find((strategy) => strategy.id === 'standing')
    ?? strategies[0];
}
