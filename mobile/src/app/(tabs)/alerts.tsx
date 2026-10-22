import { useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, View } from 'react-native';

import { Button } from '@/components/button';
import { Screen } from '@/components/screen';
import { StateView } from '@/components/state-view';
import { ThemedText } from '@/components/themed-text';
import { BottomTabInset, Spacing, type ThemeColor } from '@/constants/theme';
import { useApi } from '@/hooks/use-api';
import { useTheme } from '@/hooks/use-theme';
import { errorMessage, listNotifications, runAlertCheck, type AppNotification } from '@/lib/api';

const KINDS: Record<string, { label: string; color: ThemeColor }> = {
  digest: { label: 'Expiring soon', color: 'warning' },
  urgent: { label: 'Expires today', color: 'danger' },
  expired: { label: 'Expired', color: 'danger' },
};

/**
 * Every alert the backend has sent, newest first. They're stored even when the
 * push fails, so this list is complete whether or not push notifications work.
 */
export default function AlertsScreen() {
  const theme = useTheme();
  const { data: notifications, error, loading, reload } = useApi(listNotifications);
  const [running, setRunning] = useState(false);
  const [runSummary, setRunSummary] = useState<string | null>(null);

  // The backend runs this check every morning; the button runs it now (handy for demos).
  async function runCheck() {
    setRunning(true);
    try {
      const run = await runAlertCheck();
      const total = run.soon + run.urgent + run.expired;
      setRunSummary(
        total === 0
          ? 'Check done: no new alerts.'
          : `Check done: ${run.soon} expiring soon, ${run.urgent} expiring today, ${run.expired} expired.` +
              (run.pushFailures ? ` ${run.pushFailures} push notification(s) failed.` : ''),
      );
      await reload();
    } catch (err) {
      setRunSummary(errorMessage(err));
    } finally {
      setRunning(false);
    }
  }

  let content;
  if (notifications === null) {
    content = error ? (
      <StateView kind="error" message={error} onRetry={reload} />
    ) : (
      <StateView kind="loading" />
    );
  } else {
    content = (
      <FlatList
        data={notifications}
        keyExtractor={(n) => String(n.id)}
        renderItem={({ item }) => <NotificationCard notification={item} />}
        refreshControl={<RefreshControl refreshing={loading && !running} onRefresh={reload} />}
        ListHeaderComponent={
          error ? <ThemedText themeColor="danger">{error}</ThemedText> : null
        }
        ListEmptyComponent={
          <StateView kind="empty" message="No alerts yet. You'll be told here when food is about to expire." />
        }
        contentContainerStyle={styles.list}
      />
    );
  }

  return (
    <Screen title="Alerts">
      <View style={styles.actions}>
        <Button title="Run expiry check now" variant="secondary" onPress={runCheck} busy={running} />
        {runSummary && (
          <ThemedText type="small" themeColor="textSecondary" accessibilityLiveRegion="polite">
            {runSummary}
          </ThemedText>
        )}
      </View>
      <View style={[styles.body, { borderTopColor: theme.backgroundElement }]}>{content}</View>
    </Screen>
  );
}

function NotificationCard({ notification }: { notification: AppNotification }) {
  const theme = useTheme();
  const kind = KINDS[notification.kind] ?? { label: notification.kind, color: 'textSecondary' };
  const when = new Date(notification.createdAt).toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
  });

  return (
    <View style={[styles.card, { backgroundColor: theme.backgroundElement }]}>
      <View style={styles.cardTop}>
        <ThemedText type="smallBold" themeColor={kind.color}>
          {kind.label}
        </ThemedText>
        <ThemedText type="small" themeColor="textSecondary">
          {when}
        </ThemedText>
      </View>
      <ThemedText style={styles.title}>{notification.title}</ThemedText>
      <ThemedText type="small">{notification.body}</ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  actions: {
    gap: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingBottom: Spacing.three,
  },
  body: {
    flex: 1,
    borderTopWidth: 1,
  },
  list: {
    flexGrow: 1,
    gap: Spacing.three,
    padding: Spacing.three,
    paddingBottom: BottomTabInset + Spacing.three,
  },
  card: {
    gap: Spacing.one,
    padding: Spacing.three,
    borderRadius: Spacing.three,
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  title: {
    fontWeight: 600,
  },
});
