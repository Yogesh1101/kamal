import { router } from 'expo-router';
import { FlatList, Pressable, RefreshControl, StyleSheet, View } from 'react-native';

import { Screen } from '@/components/screen';
import { StateView } from '@/components/state-view';
import { ThemedText } from '@/components/themed-text';
import { BottomTabInset, Spacing } from '@/constants/theme';
import { useApi } from '@/hooks/use-api';
import { useTheme } from '@/hooks/use-theme';
import { listItems, type Item } from '@/lib/api';
import { describeDaysLeft, expiryTone } from '@/lib/dates';

/** Everything in the kitchen, soonest expiry first (the backend sorts it). */
export default function InventoryScreen() {
  const theme = useTheme();
  const { data: items, error, loading, reload } = useApi(listItems);

  let content;
  if (items === null) {
    content = error ? (
      <StateView kind="error" message={error} onRetry={reload} />
    ) : (
      <StateView kind="loading" />
    );
  } else {
    content = (
      <FlatList
        data={items}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => <ItemRow item={item} />}
        ItemSeparatorComponent={() => (
          <View style={[styles.separator, { backgroundColor: theme.backgroundElement }]} />
        )}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={reload} />}
        ListHeaderComponent={
          error ? <ThemedText themeColor="danger" style={styles.banner}>{error}</ThemedText> : null
        }
        ListEmptyComponent={
          <StateView kind="empty" message="Nothing in the kitchen yet. Scan an item to add it." />
        }
        contentContainerStyle={styles.list}
      />
    );
  }

  return <Screen title="Kitchen">{content}</Screen>;
}

function ItemRow({ item }: { item: Item }) {
  const details = [item.category, item.quantity > 1 ? `× ${item.quantity}` : null, item.brand]
    .filter(Boolean)
    .join(' · ');

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityHint="Opens the item to edit it"
      onPress={() => router.push({ pathname: '/item/[id]', params: { id: String(item.id) } })}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
      <View style={styles.rowText}>
        <ThemedText numberOfLines={1}>{item.name}</ThemedText>
        <ThemedText type="small" themeColor="textSecondary" numberOfLines={1}>
          {details}
        </ThemedText>
      </View>
      <ThemedText type="smallBold" themeColor={expiryTone(item.daysLeft)}>
        {describeDaysLeft(item.daysLeft)}
      </ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  list: {
    flexGrow: 1,
    paddingBottom: BottomTabInset,
  },
  banner: {
    padding: Spacing.three,
  },
  row: {
    minHeight: 64,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  pressed: {
    opacity: 0.6,
  },
  rowText: {
    flex: 1,
  },
  separator: {
    height: 1,
    marginHorizontal: Spacing.three,
  },
});
