import DateTimePicker, { DateTimePickerAndroid } from "@react-native-community/datetimepicker";
import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import { Alert, Platform, Pressable, ScrollView, StyleSheet, TextInput, useColorScheme, View } from "react-native";

import { Button } from "@/components/button";
import { Chip } from "@/components/chip";
import { StateView } from "@/components/state-view";
import { ThemedText } from "@/components/themed-text";
import { ThemedView } from "@/components/themed-view";
import { Spacing } from "@/constants/theme";
import { useApi } from "@/hooks/use-api";
import { useTheme } from "@/hooks/use-theme";
import {
  deleteItem,
  errorMessage,
  getItem,
  listCategories,
  updateItem,
  type Category,
  type Item,
  type ItemChanges,
} from "@/lib/api";
import { formatDate, parseDate, toIsoDate } from "@/lib/dates";

export default function ItemScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const load = useCallback(() => Promise.all([getItem(Number(id)), listCategories()]), [id]);
  const { data, error, reload } = useApi(load);

  return (
    <ThemedView style={styles.container}>
      {data ? (
        // `key` gives each item a fresh form; reloads of the same item keep unsaved edits.
        <ItemForm key={data[0].id} item={data[0]} categories={data[1]} />
      ) : error ? (
        <StateView kind="error" message={error} onRetry={reload} />
      ) : (
        <StateView kind="loading" />
      )}
    </ThemedView>
  );
}

function ItemForm({ item, categories }: { item: Item; categories: Category[] }) {
  const theme = useTheme();
  const scheme = useColorScheme();
  const [name, setName] = useState(item.name);
  const [category, setCategory] = useState(item.category);
  const [quantity, setQuantity] = useState(item.quantity);
  const [expiryDate, setExpiryDate] = useState(item.expiryDate);
  const [busy, setBusy] = useState<"save" | "used" | "discard" | "delete" | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Only send what changed (PATCH), so the backend keeps everything else as it is.
  const changes: ItemChanges = {};
  if (name.trim() !== item.name) changes.name = name.trim();
  if (category !== item.category) changes.category = category;
  if (quantity !== item.quantity) changes.quantity = quantity;
  if (expiryDate !== item.expiryDate) changes.expiryDate = expiryDate;
  const dirty = Object.keys(changes).length > 0;

  async function act(kind: NonNullable<typeof busy>, action: () => Promise<unknown>) {
    setBusy(kind);
    setError(null);
    try {
      await action();
      router.back();
    } catch (err) {
      setError(errorMessage(err));
      setBusy(null);
    }
  }

  function pickDate() {
    // Android only: shows the system calendar dialog; nothing to render ourselves.
    DateTimePickerAndroid.open({
      value: parseDate(expiryDate),
      mode: "date",
      onValueChange: (_event, date) => setExpiryDate(toIsoDate(date)),
      // Without this, the picker swallows native errors and simply doesn't open.
      onError: (err) => Alert.alert("Couldn't open the date picker", errorMessage(err)),
    });
  }

  function confirmDelete() {
    Alert.alert("Delete item?", `"${item.name}" will be removed for good.`, [
      { text: "Cancel", style: "cancel" },
      { text: "Delete", style: "destructive", onPress: () => act("delete", () => deleteItem(item.id)) },
    ]);
  }

  const inputStyle = [styles.input, { color: theme.text, backgroundColor: theme.backgroundElement }];

  return (
    <ScrollView
      contentContainerStyle={styles.form}
      keyboardShouldPersistTaps="handled"
      keyboardDismissMode="on-drag"
      automaticallyAdjustKeyboardInsets
    >
      <View style={styles.field}>
        <ThemedText type="smallBold" nativeID="nameLabel">
          Name
        </ThemedText>
        <TextInput
          value={name}
          onChangeText={setName}
          accessibilityLabel="Name"
          accessibilityLabelledBy="nameLabel"
          style={inputStyle}
        />
        {item.barcode && (
          <ThemedText type="small" themeColor="textSecondary">
            Barcode {item.barcode}
            {item.brand ? ` · ${item.brand}` : ""}
          </ThemedText>
        )}
      </View>

      <View style={styles.field}>
        <ThemedText type="smallBold">Category</ThemedText>
        <View style={styles.chips}>
          {categories.map((c) => (
            <Chip key={c.name} label={c.name} selected={category === c.name} onPress={() => setCategory(c.name)} />
          ))}
        </View>
        <ThemedText type="small" themeColor="textSecondary">
          {"Changing the category doesn't move the expiry date; set it below."}
        </ThemedText>
      </View>

      <View style={styles.field}>
        <ThemedText type="smallBold">Quantity</ThemedText>
        <View style={styles.stepper}>
          <StepButton
            label="−"
            a11y="Decrease quantity"
            disabled={quantity <= 1}
            onPress={() => setQuantity(quantity - 1)}
          />
          <ThemedText type="subtitle" style={styles.quantity} accessibilityLiveRegion="polite">
            {quantity}
          </ThemedText>
          <StepButton label="+" a11y="Increase quantity" onPress={() => setQuantity(quantity + 1)} />
        </View>
      </View>

      <View style={styles.field}>
        <ThemedText type="smallBold">Expiry date</ThemedText>
        {Platform.OS === "ios" ? (
          // iOS: a native date button that opens a calendar popover.
          <DateTimePicker
            value={parseDate(expiryDate)}
            mode="date"
            display="compact"
            onValueChange={(_event, date) => setExpiryDate(toIsoDate(date))}
            themeVariant={scheme === "dark" ? "dark" : "light"}
            accentColor={theme.tint}
            accessibilityLabel="Expiry date"
            style={styles.iosDatePicker}
          />
        ) : (
          // Android: a row that opens the system calendar dialog.
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Expiry date ${formatDate(expiryDate)}. Change`}
            onPress={pickDate}
            style={[inputStyle, styles.dateButton]}
          >
            <ThemedText>{formatDate(expiryDate)}</ThemedText>
            <ThemedText type="small" themeColor="tint">
              Change
            </ThemedText>
          </Pressable>
        )}
      </View>

      {error && (
        <ThemedText themeColor="danger" accessibilityLiveRegion="polite">
          {error}
        </ThemedText>
      )}

      <Button
        title="Save changes"
        onPress={() => act("save", () => updateItem(item.id, changes))}
        busy={busy === "save"}
        disabled={!dirty || name.trim() === "" || busy !== null}
      />
      <View style={styles.row}>
        <View style={styles.grow}>
          <Button
            title="Used it up"
            variant="secondary"
            onPress={() => act("used", () => updateItem(item.id, { status: "consumed" }))}
            busy={busy === "used"}
            disabled={busy !== null}
          />
        </View>
        <View style={styles.grow}>
          <Button
            title="Threw it away"
            variant="secondary"
            onPress={() => act("discard", () => updateItem(item.id, { status: "discarded" }))}
            busy={busy === "discard"}
            disabled={busy !== null}
          />
        </View>
      </View>
      <Button
        title="Delete item"
        variant="danger"
        onPress={confirmDelete}
        busy={busy === "delete"}
        disabled={busy !== null}
      />
    </ScrollView>
  );
}

function StepButton({
  label,
  a11y,
  onPress,
  disabled = false,
}: {
  label: string;
  a11y: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={a11y}
      disabled={disabled}
      onPress={onPress}
      style={[styles.stepButton, { backgroundColor: theme.backgroundElement, opacity: disabled ? 0.4 : 1 }]}
    >
      <ThemedText type="subtitle">{label}</ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  form: {
    gap: Spacing.four,
    padding: Spacing.three,
    paddingBottom: Spacing.six,
  },
  field: {
    gap: Spacing.two,
  },
  input: {
    minHeight: 48,
    borderRadius: Spacing.three,
    paddingHorizontal: Spacing.three,
    fontSize: 16,
  },
  chips: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: Spacing.two,
  },
  stepper: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.four,
  },
  stepButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: "center",
    justifyContent: "center",
  },
  quantity: {
    minWidth: 40,
    textAlign: "center",
  },
  iosDatePicker: {
    alignSelf: "flex-start",
  },
  dateButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  row: {
    flexDirection: "row",
    gap: Spacing.three,
  },
  grow: {
    flex: 1,
  },
});
