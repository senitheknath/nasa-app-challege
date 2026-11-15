import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Keyboard, Platform, type ViewProps } from 'react-native';

export function useSearchFocus() {
  const [focused, setFocused] = useState(false);
  const dismiss = () => {
    setFocused(false);
    Keyboard.dismiss();
  };
  useFocusEffect(useCallback(() => () => setFocused(false), []));

  useEffect(() => {
    if (Platform.OS === 'web') return;
    const keyboard = Keyboard.addListener('keyboardDidHide', () => setFocused(false));
    return () => keyboard.remove();
  }, []);

  const onBlur: ViewProps['onBlur'] = (event) => {
    // On web, focus can move from the input to a suggestion within the same panel.
    const next = 'relatedTarget' in event ? event.relatedTarget : null;
    const panel = event.currentTarget;
    if (!(panel instanceof Node && next instanceof Node && panel.contains(next))) setFocused(false);
  };
  const onKeyDownCapture: ViewProps['onKeyDownCapture'] = (event) => {
    const key = 'key' in event ? event.key : event.nativeEvent.key;
    if (key === 'Escape') {
      event.preventDefault();
      dismiss();
    }
  };

  return {
    focused,
    open: () => setFocused(true),
    dismiss,
    panelProps: Platform.OS === 'web' ? { onBlur, onKeyDownCapture } : {},
  };
}
