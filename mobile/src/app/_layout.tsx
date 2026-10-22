import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import { useColorScheme } from 'react-native';

/**
 * Root navigator: a stack. The tab bar is its first screen, and the item editor
 * slides in on top of it (so it gets a back button and hides the tabs).
 */
export default function RootLayout() {
  const colorScheme = useColorScheme();
  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="item/[id]"
          // iOS labels the back button with the previous screen's title, which falls back
          // to its route name, "(tabs)". Show just the arrow, as Android does.
          options={{ title: 'Edit item', headerBackButtonDisplayMode: 'minimal' }}
        />
      </Stack>
    </ThemeProvider>
  );
}
