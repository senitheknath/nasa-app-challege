import { selectionAsync } from 'expo-haptics';

export function tap() {
  void selectionAsync().catch(() => undefined);
}
