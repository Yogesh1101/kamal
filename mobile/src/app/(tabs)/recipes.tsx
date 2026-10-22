import { useCallback, useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, View } from 'react-native';

import { Chip } from '@/components/chip';
import { Screen } from '@/components/screen';
import { StateView } from '@/components/state-view';
import { ThemedText } from '@/components/themed-text';
import { BottomTabInset, Spacing } from '@/constants/theme';
import { useApi } from '@/hooks/use-api';
import { useTheme } from '@/hooks/use-theme';
import { listRecipes, type AiStatus, type Diet, type Recipe } from '@/lib/api';
import { describeDaysLeft } from '@/lib/dates';

const DIETS: { label: string; value: Diet | undefined }[] = [
  { label: 'All', value: undefined },
  { label: 'Veg', value: 'vegetarian' },
  { label: 'Non-veg', value: 'non vegetarian' },
];

const AI_NOTES: Partial<Record<AiStatus, string>> = {
  generated: 'Few recipes in the dataset matched, so some ideas come from Gemini.',
  cached: 'Few recipes in the dataset matched, so some ideas come from Gemini.',
  unavailable: 'Few recipes matched, and Gemini ideas are unavailable right now.',
};

/** Recipes that use up food expiring soon, best first (the backend ranks them). */
export default function RecipesScreen() {
  const theme = useTheme();
  const [diet, setDiet] = useState<Diet | undefined>(undefined);
  const [expanded, setExpanded] = useState<string | null>(null);
  const load = useCallback(() => listRecipes(diet), [diet]);
  const { data, error, loading, reload } = useApi(load);

  const filters = (
    <View style={styles.filters} accessibilityRole="radiogroup">
      {DIETS.map((d) => (
        <Chip key={d.label} label={d.label} selected={diet === d.value} onPress={() => setDiet(d.value)} />
      ))}
    </View>
  );

  let content;
  if (data === null) {
    content = error ? (
      <StateView kind="error" message={error} onRetry={reload} />
    ) : (
      // The first load can wait on Gemini, which takes a few seconds.
      <StateView kind="loading" message="Finding recipes for what's expiring…" />
    );
  } else {
    const note = AI_NOTES[data.aiStatus];
    content = (
      <FlatList
        data={data.recipes}
        keyExtractor={(r) => `${r.source}:${r.name}`}
        renderItem={({ item }) => {
          const key = `${item.source}:${item.name}`;
          return (
            <RecipeCard
              recipe={item}
              expanded={expanded === key}
              onToggle={() => setExpanded(expanded === key ? null : key)}
            />
          );
        }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={reload} />}
        ListHeaderComponent={
          <>
            {error && <ThemedText themeColor="danger">{error}</ThemedText>}
            {note && (
              <ThemedText type="small" themeColor="textSecondary">
                {note}
              </ThemedText>
            )}
          </>
        }
        ListEmptyComponent={
          <StateView kind="empty" message="No recipes yet. Add some items to your kitchen first." />
        }
        contentContainerStyle={styles.list}
      />
    );
  }

  return (
    <Screen title="Recipes">
      {filters}
      <View style={[styles.body, { borderTopColor: theme.backgroundElement }]}>{content}</View>
    </Screen>
  );
}

function RecipeCard({
  recipe,
  expanded,
  onToggle,
}: {
  recipe: Recipe;
  expanded: boolean;
  onToggle: () => void;
}) {
  const theme = useTheme();
  const facts = [
    recipe.source === 'gemini' ? 'AI idea' : null,
    recipe.course,
    recipe.totalTimeMinutes ? `${recipe.totalTimeMinutes} min` : null,
    recipe.diet === 'vegetarian' ? 'veg' : 'non-veg',
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ expanded }}
      onPress={onToggle}
      style={[styles.card, { backgroundColor: theme.backgroundElement }]}>
      <ThemedText type="default" style={styles.cardTitle}>
        {recipe.name}
      </ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {facts}
      </ThemedText>

      {recipe.usedItems.length > 0 && (
        <ThemedText type="small">
          <ThemedText type="smallBold">Uses: </ThemedText>
          {recipe.usedItems
            .map((u) => `${u.name} (${describeDaysLeft(u.daysLeft).toLowerCase()})`)
            .join(', ')}
        </ThemedText>
      )}
      {recipe.missingIngredients.length > 0 && (
        <ThemedText type="small" themeColor="textSecondary">
          <ThemedText type="smallBold" themeColor="textSecondary">
            {"You'd also need: "}
          </ThemedText>
          {recipe.missingIngredients.join(', ')}
        </ThemedText>
      )}

      {expanded && (
        <View style={styles.details}>
          <ThemedText type="smallBold">Ingredients</ThemedText>
          <ThemedText type="small">{recipe.ingredients.join(', ')}</ThemedText>
          {recipe.steps.length > 0 && (
            <>
              <ThemedText type="smallBold">Steps</ThemedText>
              {recipe.steps.map((step, i) => (
                <ThemedText key={i} type="small">
                  {i + 1}. {step}
                </ThemedText>
              ))}
            </>
          )}
        </View>
      )}
      <ThemedText type="small" themeColor="tint">
        {expanded ? 'Show less' : 'Show ingredients'}
      </ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  filters: {
    flexDirection: 'row',
    gap: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingBottom: Spacing.two,
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
  cardTitle: {
    fontWeight: 600,
  },
  details: {
    gap: Spacing.one,
    marginTop: Spacing.two,
  },
});
