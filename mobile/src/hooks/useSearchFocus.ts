import { useEffect, useRef, useState } from 'react';
import { Keyboard } from 'react-native';

export function useSearchFocus() {
  const [focused, setFocused] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  return {
    focused,
    onFocus: () => { clearTimeout(timer.current); setFocused(true); },
    onBlur: () => { timer.current = setTimeout(() => setFocused(false), 180); },
    dismiss: () => { clearTimeout(timer.current); setFocused(false); Keyboard.dismiss(); },
  };
}
