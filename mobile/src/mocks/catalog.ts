import type { PlaceDto } from '@/features/area/model';
import type { CountryDto } from '@/features/country/model';
import type { CropDto } from '@/features/crop/model';
import type { StrategyDto } from '@/features/strategy/model';

const names = [
  ['AF', 'Afghanistan'], ['AL', 'Albania'], ['DZ', 'Algeria'], ['AR', 'Argentina'], ['AU', 'Australia'],
  ['BD', 'Bangladesh'], ['BR', 'Brazil'], ['IN', 'India'], ['KE', 'Kenya'], ['NP', 'Nepal'],
  ['LK', 'Sri Lanka'], ['TH', 'Thailand'], ['VN', 'Vietnam'],
];
export const countries: CountryDto[] = names.map(([id, name]) => ({ id, name, supported: id === 'LK' }));

export const categories = [
  { id: 'cereals', label: 'Cereals' }, { id: 'legumes', label: 'Legumes' }, { id: 'vegetables', label: 'Vegetables' },
  { id: 'roots', label: 'Roots' }, { id: 'perennial', label: 'Perennial' },
];

function crop(id: string, name: string, category: number, yieldTonnesPerHectare: number, waterPercent: number): CropDto {
  return { id, name, category: categories[category], yieldTonnesPerHectare, waterPercent };
}
export const crops = [
  crop('rice', 'Paddy Rice', 0, 5.2, 85), crop('maize', 'Maize', 0, 7.5, 55),
  crop('green-gram', 'Green Gram', 1, 1.2, 35), crop('groundnut', 'Groundnut', 1, 2.1, 40),
  crop('chili', 'Chili', 2, 3.4, 50), crop('red-onion', 'Red Onion', 2, 14, 55),
  crop('cassava', 'Cassava', 3, 18, 40), crop('sugarcane', 'Sugarcane', 4, 62, 80),
  crop('tea', 'Estate Tea', 4, 2.4, 60), crop('coconut', 'Coconut', 4, 6.8, 65),
];

export const strategies: StrategyDto[] = [
  { id: 'fallow', tag: 'Fallow', title: 'No rotation', description: 'Newly cleared land', requiresCrop: false },
  { id: 'standing', tag: 'Standing', title: 'Current crop', description: 'Already planted', requiresCrop: true },
  { id: 'rotation', tag: 'Rotation', title: 'Rotation cycle', description: 'Maha and Yala seasons', requiresCrop: true },
];

export const places: PlaceDto[] = [
  { id: 'anuradhapura', name: 'Anuradhapura' }, { id: 'dambulla', name: 'Dambulla' },
  { id: 'hambantota', name: 'Hambantota' }, { id: 'kandy', name: 'Kandy' },
  { id: 'polonnaruwa', name: 'Polonnaruwa' },
];

export const aerialUrl = 'https://images.unsplash.com/photo-1508175688576-0c076b47b5b5?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080';
