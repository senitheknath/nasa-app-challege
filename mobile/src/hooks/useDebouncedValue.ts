import { useEffect, useState } from 'react';
import { motion } from '@/theme/tokens';

export function useDebouncedValue(value: string) {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timeout = setTimeout(() => setSettled(value), motion.search);
    return () => clearTimeout(timeout);
  }, [value]);
  return settled;
}
