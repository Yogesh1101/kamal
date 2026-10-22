/**
 * Talks to the FastAPI backend (backend/app). Every response is wrapped:
 * {data} for one thing, {data, meta} for a list, {error: {code, message}} on failure.
 * These functions unwrap {data} so screens get plain objects.
 */

import { File } from 'expo-file-system';

// Inlined at bundle time from mobile/.env: EXPO_PUBLIC_API_URL=http://<laptop-ip>:8000/api/v1
// (restart with `npx expo start -c` after changing it).
const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? '';

const TIMEOUT_MS = 15_000;
// A new barcode is looked up on Open Food Facts, which can be slow over a phone hotspot.
const SCAN_TIMEOUT_MS = 30_000;
// Recipes can wait on Gemini when the dataset has too few matches.
const RECIPES_TIMEOUT_MS = 45_000;

// ---- Shapes (mirror backend/app/schemas.py) ----

export type ItemStatus = 'active' | 'consumed' | 'discarded';

export type Item = {
  id: number;
  barcode: string | null;
  name: string;
  brand: string | null;
  category: string;
  quantity: number;
  addedOn: string; // YYYY-MM-DD
  expiryDate: string; // YYYY-MM-DD
  daysLeft: number;
  status: ItemStatus;
};

export type ItemChanges = Partial<
  Pick<Item, 'name' | 'category' | 'brand' | 'quantity' | 'expiryDate' | 'status'>
>;

export type Category = {
  name: string;
  shelfLifeDays: number;
  alertDaysBefore: number;
};

export type ScanResult = {
  code: string;
  source: 'cache' | 'open_food_facts' | 'label' | 'unknown';
  item: Item;
};

export type AppNotification = {
  id: number;
  kind: string; // digest | urgent | expired
  title: string;
  body: string;
  createdAt: string;
};

export type AlertRun = {
  date: string;
  soon: number;
  urgent: number;
  expired: number;
  pushFailures: number;
};

export type Diet = 'vegetarian' | 'non vegetarian';

export type Recipe = {
  name: string;
  source: 'dataset' | 'gemini';
  score: number;
  goodMatch: boolean;
  coverage: number;
  usedItems: { id: number; name: string; daysLeft: number }[];
  missingIngredients: string[];
  ingredients: string[];
  steps: string[];
  diet: Diet;
  course: string | null;
  totalTimeMinutes: number | null;
};

export type PageMeta = { page: number; pageSize: number; totalPages: number; totalCount: number };
export type AiStatus = 'not_needed' | 'cached' | 'generated' | 'unavailable';

type Envelope<T> = { data: T };
type Page<T, M = PageMeta> = { data: T[]; meta: M };

// ---- Errors ----

export class ApiError extends Error {
  constructor(
    readonly status: number, // 0 when the backend couldn't be reached
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

// ---- Request helper ----

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = TIMEOUT_MS): Promise<T> {
  if (!BASE_URL) {
    throw new ApiError(0, 'NO_API_URL', 'Backend address not set: add EXPO_PUBLIC_API_URL to mobile/.env');
  }
  // fetch has no timeout of its own; without one, a wrong IP spins forever.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(BASE_URL + path, {
      ...init,
      headers: { Accept: 'application/json', ...init.headers },
      signal: controller.signal,
    });
  } catch (err) {
    if (controller.signal.aborted) {
      throw new ApiError(0, 'TIMEOUT', `The backend at ${BASE_URL} didn't answer within ${timeoutMs / 1000} s.`);
    }
    // Keep the underlying reason: "can't reach" alone hides app-side errors (e.g. a bad request body).
    throw new ApiError(
      0,
      'NETWORK_ERROR',
      `Can't reach the backend at ${BASE_URL} (${errorMessage(err)}). Is it running, and is the phone on the same Wi-Fi?`,
    );
  } finally {
    clearTimeout(timer);
  }

  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const error = body?.error;
    throw new ApiError(
      res.status,
      error?.code ?? 'HTTP_ERROR',
      error?.message ?? `Request failed (HTTP ${res.status})`,
    );
  }
  return body as T;
}

function sendJson(method: string, body: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

// ---- Endpoints ----

export async function listItems(status: ItemStatus = 'active'): Promise<Item[]> {
  // 100 is the backend's page-size limit: plenty for one household's kitchen.
  const page = await request<Page<Item>>(`/items?status=${status}&pageSize=100`);
  return page.data;
}

export async function getItem(id: number): Promise<Item> {
  return (await request<Envelope<Item>>(`/items/${id}`)).data;
}

export async function updateItem(id: number, changes: ItemChanges): Promise<Item> {
  return (await request<Envelope<Item>>(`/items/${id}`, sendJson('PATCH', changes))).data;
}

export async function deleteItem(id: number): Promise<void> {
  await request<void>(`/items/${id}`, { method: 'DELETE' });
}

export async function listCategories(): Promise<Category[]> {
  return (await request<Page<Category>>('/categories?pageSize=100')).data;
}

/**
 * Upload a photo; the backend finds the barcode/QR code in it and adds the item.
 * The raw image bytes go to /scans/jpeg, the same endpoint the ESP32-CAM uses.
 * (Expo's fetch can't send React Native's {uri, name, type} FormData files.)
 */
export async function scanImage(photo: { uri: string; mimeType?: string | null }): Promise<ScanResult> {
  const bytes = await new File(photo.uri).arrayBuffer();
  const init: RequestInit = {
    method: 'POST',
    headers: { 'Content-Type': photo.mimeType ?? 'image/jpeg' },
    body: bytes,
  };
  return (await request<Envelope<ScanResult>>('/scans/jpeg', init, SCAN_TIMEOUT_MS)).data;
}

/** Add an item from a barcode typed in by hand. */
export async function scanCode(code: string): Promise<ScanResult> {
  return (await request<Envelope<ScanResult>>('/scans/codes', sendJson('POST', { code }), SCAN_TIMEOUT_MS)).data;
}

export async function listNotifications(): Promise<AppNotification[]> {
  return (await request<Page<AppNotification>>('/notifications?pageSize=50')).data;
}

/** Run the daily expiry check now instead of waiting for the scheduled time. */
export async function runAlertCheck(): Promise<AlertRun> {
  return (await request<Envelope<AlertRun>>('/alert-runs', sendJson('POST', {}))).data;
}

export async function listRecipes(
  diet?: Diet,
): Promise<{ recipes: Recipe[]; aiStatus: AiStatus }> {
  const query = diet ? `&diet=${encodeURIComponent(diet)}` : '';
  const page = await request<Page<Recipe, PageMeta & { aiStatus: AiStatus }>>(
    `/recipe-suggestions?pageSize=20${query}`,
    {},
    RECIPES_TIMEOUT_MS,
  );
  return { recipes: page.data, aiStatus: page.meta.aiStatus };
}

/** Send this phone's FCM token so the backend can push alerts to it. */
export async function registerDevice(token: string): Promise<void> {
  await request('/devices', sendJson('POST', { token }));
}
