import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Logo } from '@/components/cards';
import { Message, PrimaryButton } from '@/components/primitives';
import { strings } from '@/i18n/strings';
import { colors, size, space } from '@/theme/tokens';

export default function SessionScreen() {
  return (
    <SafeAreaView style={styles.root}>
      <View style={styles.content}>
        <Logo />
        <Message title={strings.sessionTitle} hint={strings.sessionHint} icon="globe" />
        <PrimaryButton label={strings.home} onPress={() => router.replace('/')} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.forest950, justifyContent: 'center', paddingHorizontal: space.gutter },
  content: { gap: space.lg, width: '100%', maxWidth: size.maxContent, alignSelf: 'center' },
});
