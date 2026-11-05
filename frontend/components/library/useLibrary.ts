"use client";

import { useEffect, useState } from "react";
import {
  fetchLibrary,
  fetchLibrarySummary,
  removeFromLibrary,
  updateLibraryItem,
  type LibraryItem,
  type LibraryItemChanges,
  type LibraryQuery,
  type LibrarySummary,
} from "@/lib/library";

interface Loaded {
  key: string;
  items: LibraryItem[];
  error: string;
}

/** Whether an entry still belongs in a list loaded with `query`. */
function matchesQuery(item: LibraryItem, query: LibraryQuery): boolean {
  if (query.ownership && item.ownership !== query.ownership) return false;
  if (query.played === "played" && !item.has_played) return false;
  if (query.played === "unplayed" && item.has_played) return false;
  return true;
}

/**
 * The library entries matching `query`, the library's counts, and actions that
 * change an entry and keep both in step.
 *
 * Results are stored with the query they answer (see useRecommendations), so
 * an older response is never shown for a newer query.
 */
export function useLibrary(query: LibraryQuery) {
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [summary, setSummary] = useState<LibrarySummary | null>(null);
  const [version, setVersion] = useState(0);
  const queryKey = JSON.stringify(query);
  const loadKey = `${queryKey}#${version}`;

  useEffect(() => {
    const controller = new AbortController();

    fetchLibrary(JSON.parse(queryKey), controller.signal)
      .then((items) => {
        if (!controller.signal.aborted) {
          setLoaded({ key: loadKey, items, error: "" });
        }
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          key: loadKey,
          items: [],
          error: err instanceof Error ? err.message : "Something went wrong.",
        });
      });

    return () => controller.abort();
  }, [queryKey, loadKey]);

  useEffect(() => {
    const controller = new AbortController();

    fetchLibrarySummary(controller.signal)
      .then((counts) => {
        if (!controller.signal.aborted) setSummary(counts);
      })
      .catch(() => {
        // The counts are a nicety; the list still works without them.
      });

    return () => controller.abort();
  }, [version]);

  const current = loaded?.key === loadKey ? loaded : null;

  function setItems(update: (items: LibraryItem[]) => LibraryItem[]) {
    setLoaded((previous) =>
      previous ? { ...previous, items: update(previous.items) } : previous,
    );
  }

  /** Save changes to an entry, dropping it from view if it no longer matches. */
  async function update(gameId: number, changes: LibraryItemChanges) {
    const saved = await updateLibraryItem(gameId, changes);
    setItems((items) =>
      items.flatMap((item) => {
        if (item.game.bgg_id !== gameId) return [item];
        return matchesQuery(saved, query) ? [saved] : [];
      }),
    );
    refreshSummary();
    return saved;
  }

  async function remove(gameId: number) {
    await removeFromLibrary(gameId);
    setItems((items) => items.filter((item) => item.game.bgg_id !== gameId));
    refreshSummary();
  }

  function refreshSummary() {
    fetchLibrarySummary()
      .then(setSummary)
      .catch(() => undefined);
  }

  return {
    items: current?.items ?? [],
    loading: current === null,
    error: current?.error ?? "",
    summary,
    update,
    remove,
    /** Load the list and counts again, e.g. after a BGG import. */
    reload: () => setVersion((value) => value + 1),
  };
}
