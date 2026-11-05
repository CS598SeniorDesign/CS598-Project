"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import BggImportButton from "@/components/library/BggImportButton";
import LibraryCard from "@/components/library/LibraryCard";
import LibraryToolbar from "@/components/library/LibraryToolbar";
import { useLibrary } from "@/components/library/useLibrary";
import { useRatings } from "@/components/ratings/useRatings";
import type {
  LibraryItem,
  LibraryItemChanges,
  LibrarySummary,
  Ownership,
  PlayedFilter,
} from "@/lib/library";
import type { Rating } from "@/lib/ratings";

/** How long to wait after the last keystroke before searching, in ms. */
const SEARCH_DELAY = 300;
const DEFAULT_ORDERING = "-added_at";

const TABS: {
  key: Ownership;
  label: string;
  countKey: keyof LibrarySummary;
}[] = [
  { key: "OWNED", label: "Library", countKey: "owned" },
  { key: "WISHLISTED", label: "Wishlist", countKey: "wishlisted" },
];

/** `value`, updated only once it has stopped changing for `delay` ms. */
function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

function EmptyLibrary({
  filtered,
  ownership,
}: {
  filtered: boolean;
  ownership: Ownership;
}) {
  let message = "Your library is empty. Add some games to get started!";

  if (filtered) {
    message = "No games match your search.";
  } else if (ownership === "WISHLISTED") {
    message = "Your wishlist is empty for now.";
  }

  return (
    <div className="mt-12 text-center">
      <p className="text-lg text-gray-400">{message}</p>

      {!filtered && (
        <Link
          href="/games/search"
          className="mt-5 inline-block rounded-full bg-indigo-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500"
        >
          + Add Your First Game
        </Link>
      )}
    </div>
  );
}

function LibraryGrid({
  items,
  loading,
  error,
  filtered,
  ownership,
  onUpdate,
  onRemove,
  ratings,
  onRatingChange,
}: {
  items: LibraryItem[];
  loading: boolean;
  error: string;
  filtered: boolean;
  ownership: Ownership;
  onUpdate: (gameId: number, changes: LibraryItemChanges) => Promise<unknown>;
  onRemove: (gameId: number) => Promise<void>;
  ratings: Record<number, Rating>;
  onRatingChange: (gameId: number, rating: Rating | null) => void;
}) {
  if (loading) {
    return (
      <p role="status" className="mt-12 text-center text-gray-400">
        Loading your games...
      </p>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="mx-auto mt-12 max-w-lg rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-center text-red-300"
      >
        {error}
      </div>
    );
  }

  if (items.length === 0) {
    return <EmptyLibrary filtered={filtered} ownership={ownership} />;
  }

  return (
    <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {items.map((item) => (
        <LibraryCard
          key={item.game.bgg_id}
          item={item}
          onUpdate={onUpdate}
          onRemove={onRemove}
          rating={ratings[item.game.bgg_id] ?? null}
          onRatingChange={onRatingChange}
        />
      ))}
    </div>
  );
}

function SummaryLine({
  summary,
  ownership,
}: {
  summary: LibrarySummary | null;
  ownership: Ownership;
}) {
  if (!summary) return null;

  const unplayed =
    ownership === "OWNED"
      ? summary.owned_unplayed
      : summary.wishlisted_unplayed;
  if (unplayed === 0) return null;

  return (
    <p className="mt-1 text-sm text-gray-500">
      {unplayed} {unplayed === 1 ? "game" : "games"} not played yet
    </p>
  );
}

export default function LibraryPage() {
  const [ownership, setOwnership] = useState<Ownership>("OWNED");
  const [search, setSearch] = useState("");
  const [played, setPlayed] = useState<PlayedFilter>("all");
  const [ordering, setOrdering] = useState(DEFAULT_ORDERING);
  const debouncedSearch = useDebounced(search, SEARCH_DELAY);

  const library = useLibrary({
    ownership,
    search: debouncedSearch.trim() || undefined,
    played,
    ordering,
  });

  const { ratings, setRating } = useRatings();

  const isWishlist = ownership === "WISHLISTED";
  const filtered = debouncedSearch.trim() !== "" || played !== "all";

  function switchTab(next: Ownership) {
    setOwnership(next);
    setSearch("");
    setPlayed("all");
    setOrdering(DEFAULT_ORDERING);
  }

  return (
    <div className="min-h-screen bg-[#0F172A] px-8 py-10 text-white">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-5xl font-black tracking-widest">
            {isWishlist ? "WISHLIST" : "LIBRARY"}
          </h1>
          <p className="mt-2 text-gray-400">
            {isWishlist
              ? "Board games you want to add to your collection"
              : "Board games in your QuestLog collection"}
          </p>
          <SummaryLine summary={library.summary} ownership={ownership} />
        </div>

        <div className="flex flex-wrap items-start gap-3">
          <Link
            href="/games/search"
            className="rounded-full bg-indigo-600 px-7 py-3 text-sm font-bold uppercase tracking-wider text-white transition hover:bg-indigo-500"
          >
            + Add Game
          </Link>
          <BggImportButton onImported={library.reload} />
        </div>
      </div>

      <div
        role="tablist"
        aria-label="Library or wishlist"
        className="mb-6 flex gap-2"
      >
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={ownership === tab.key}
            onClick={() => switchTab(tab.key)}
            className={`rounded-full px-6 py-2 text-sm font-bold uppercase tracking-wider transition ${
              ownership === tab.key
                ? "bg-[#F87171] text-black"
                : "bg-[#1E293B] text-gray-300 hover:bg-[#334155]"
            }`}
          >
            {tab.label}
            {library.summary && ` (${library.summary[tab.countKey]})`}
          </button>
        ))}
      </div>

      <LibraryToolbar
        ownership={ownership}
        search={search}
        played={played}
        ordering={ordering}
        onSearchChange={setSearch}
        onPlayedChange={setPlayed}
        onOrderingChange={setOrdering}
      />

      <LibraryGrid
        items={library.items}
        loading={library.loading}
        error={library.error}
        filtered={filtered}
        ownership={ownership}
        onUpdate={library.update}
        onRemove={library.remove}
        ratings={ratings}
        onRatingChange={setRating}
      />
    </div>
  );
}
