import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, Keyboard, ScrollView, StyleSheet, TextInput, View } from 'react-native';

import { Button } from '@/components/button';
import { Screen } from '@/components/screen';
import { ThemedText } from '@/components/themed-text';
import { BottomTabInset, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { errorMessage, scanCode, scanImage, type ScanResult } from '@/lib/api';
import { describeDaysLeft, formatDate } from '@/lib/dates';

const SOURCE_LABELS: Record<ScanResult['source'], string> = {
  cache: 'Known product',
  open_food_facts: 'Found on Open Food Facts',
  label: 'Kitchen QR label',
  unknown: 'Unknown product: please rename it',
};

// Enough detail for the backend to read a barcode, at a fraction of the full photo size.
const PHOTO_QUALITY = 0.6;

/**
 * The phone stands in for the ESP32-CAM: it sends a photo to the same backend
 * endpoint, and the backend finds and decodes the barcode or QR code.
 */
export default function ScanScreen() {
  const theme = useTheme();
  const [busy, setBusy] = useState<'camera' | 'gallery' | 'code' | null>(null);
  const [code, setCode] = useState('');
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(kind: 'camera' | 'gallery' | 'code', send: () => Promise<ScanResult>) {
    setBusy(kind);
    setError(null);
    setResult(null);
    try {
      setResult(await send());
      if (kind === 'code') setCode('');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function takePhoto() {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Camera permission needed', 'Allow camera access to scan barcodes.');
      return;
    }
    const photo = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: PHOTO_QUALITY });
    if (!photo.canceled) submit('camera', () => scanImage(photo.assets[0]));
  }

  async function pickPhoto() {
    const photo = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: PHOTO_QUALITY,
      // iPhones store photos as HEIC, which the backend can't decode; ask iOS for a JPEG.
      preferredAssetRepresentationMode: ImagePicker.UIImagePickerPreferredAssetRepresentationMode.Compatible,
    });
    if (!photo.canceled) submit('gallery', () => scanImage(photo.assets[0]));
  }

  function sendCode() {
    Keyboard.dismiss();
    submit('code', () => scanCode(code.trim()));
  }

  return (
    <Screen title="Scan">
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
        // iOS: scroll the barcode field above the keyboard (Android resizes the window itself).
        automaticallyAdjustKeyboardInsets>
        <ThemedText themeColor="textSecondary">
          Photograph a product barcode or a kitchen QR label. The item is added with a default
          expiry date that you can correct.
        </ThemedText>

        <Button title="Take photo" onPress={takePhoto} busy={busy === 'camera'} disabled={busy !== null} />
        <Button
          title="Choose from gallery"
          variant="secondary"
          onPress={pickPhoto}
          busy={busy === 'gallery'}
          disabled={busy !== null}
        />

        <View style={styles.codeSection}>
          <ThemedText type="smallBold" nativeID="codeLabel">
            Or type the barcode number
          </ThemedText>
          <TextInput
            value={code}
            onChangeText={setCode}
            placeholder="e.g. 8901058851427"
            placeholderTextColor={theme.textSecondary}
            keyboardType="number-pad"
            returnKeyType="done"
            onSubmitEditing={sendCode}
            accessibilityLabel="Barcode number"
            accessibilityLabelledBy="codeLabel"
            style={[styles.input, { color: theme.text, backgroundColor: theme.backgroundElement }]}
          />
          <Button
            title="Add by barcode"
            variant="secondary"
            onPress={sendCode}
            busy={busy === 'code'}
            disabled={busy !== null || code.trim() === ''}
          />
        </View>

        {error && (
          <View style={[styles.card, { backgroundColor: theme.backgroundElement }]} accessibilityLiveRegion="polite">
            <ThemedText type="smallBold" themeColor="danger">
              Scan failed
            </ThemedText>
            <ThemedText>{error}</ThemedText>
          </View>
        )}

        {result && (
          <View style={[styles.card, { backgroundColor: theme.backgroundElement }]} accessibilityLiveRegion="polite">
            <ThemedText type="smallBold" themeColor="success">
              Added · {SOURCE_LABELS[result.source]}
            </ThemedText>
            <ThemedText type="default">{result.item.name}</ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              {result.item.category} · expires {formatDate(result.item.expiryDate)} (
              {describeDaysLeft(result.item.daysLeft).toLowerCase()})
            </ThemedText>
            <Button
              title="Edit name or expiry"
              variant="secondary"
              onPress={() =>
                router.push({ pathname: '/item/[id]', params: { id: String(result.item.id) } })
              }
            />
          </View>
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: Spacing.three,
    gap: Spacing.three,
    paddingBottom: BottomTabInset + Spacing.three,
  },
  codeSection: {
    gap: Spacing.two,
    marginTop: Spacing.three,
  },
  input: {
    minHeight: 48,
    borderRadius: Spacing.three,
    paddingHorizontal: Spacing.three,
    fontSize: 16,
  },
  card: {
    gap: Spacing.two,
    padding: Spacing.three,
    borderRadius: Spacing.three,
  },
});
