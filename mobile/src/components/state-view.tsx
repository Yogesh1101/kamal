import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { Button } from '@/components/button';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

type Props =
  | { kind: 'loading'; message?: string }
  | { kind: 'error'; message: string; onRetry: () => void }
  | { kind: 'empty'; message: string };

/** What a list screen shows while loading, after an error, or when there's nothing to list. */
export function StateView(props: Props) {
  const theme = useTheme();
  return (
    <View style={styles.container}>
      {props.kind === 'loading' && <ActivityIndicator size="large" color={theme.tint} />}
      {props.message && (
        <ThemedText
          themeColor={props.kind === 'error' ? 'danger' : 'textSecondary'}
          style={styles.message}>
          {props.message}
        </ThemedText>
      )}
      {props.kind === 'error' && <Button title="Try again" variant="secondary" onPress={props.onRetry} />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.three,
    padding: Spacing.four,
  },
  message: {
    textAlign: 'center',
  },
});
