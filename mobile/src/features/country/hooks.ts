import { useQuery } from '@tanstack/react-query';
import { endpoints } from '@/api/endpoints';
import { keys } from '@/api/keys';
import { mapCountryData } from './model';

export function useCountryData() {
  return useQuery({ queryKey: keys.country(), queryFn: ({ signal }) => endpoints.countries(signal), select: mapCountryData });
}
