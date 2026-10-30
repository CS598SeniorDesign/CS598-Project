"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type BoardGame = {
  bgg_id: number;
  primary_name: string;
  year_published: number | null;
  thumbnail_url: string | null;
  average_rating: number | string | null;
  bgg_rank: number | null;
};

type LibraryItem = {
  game: BoardGame;
  ownership: "OWNED" | "WISHLISTED";
  is_played: boolean;
  house_rules: string;
  added_at: string;
  updated_at: string;
};

type LibraryTab = "OWNED" | "WISHLISTED";

type LibraryResponse =
  | LibraryItem[]
  | {
      results: LibraryItem[];
    };

function getLibraryItems(data: LibraryResponse): LibraryItem[] {
  return Array.isArray(data) ? data : data.results;
}

function getLibraryError(status: number): string {
  if (status === 401 || status === 403) {
    return "Please log in to view your library.";
  }

  return "Unable to load your library. Please try again.";
}

function useLibraryGames() {
  const [games, setGames] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function fetchLibrary() {
      try {
        const response = await fetch("/api/v1/library/", {
          method: "GET",
          credentials: "include",
          headers: {
            Accept: "application/json",
          },
          cache: "no-store",
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(getLibraryError(response.status));
        }

        const data: LibraryResponse = await response.json();
        const items = getLibraryItems(data);

        if (!Array.isArray(items)) {
          throw new Error("Unexpected response from the library API.");
        }

        if (!controller.signal.aborted) {
          setGames(items);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

        setError(err instanceof Error ? err.message : "Something went wrong.");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void fetchLibrary();

    return () => controller.abort();
  }, []);

  return { games, loading, error };
}

function GameRating({ rating }: { rating: number | string | null }) {
  const numericRating = rating == null ? null : Number(rating);

  const displayRating =
    numericRating !== null && Number.isFinite(numericRating)
      ? `★ ${numericRating.toFixed(1)} / 10`
      : "Not rated";

  return <div className="mt-2 text-center text-[#FACC15]">{displayRating}</div>;
}

function GameCard({ item }: { item: LibraryItem }) {
  const { game } = item;

  return (
    <Link
      href={`/games/${game.bgg_id}`}
      className="block rounded-2xl bg-[#1E293B]/70 p-3 transition hover:-translate-y-1 hover:shadow-xl hover:shadow-indigo-500/20"
    >
      {game.thumbnail_url ? (
        <Image
          src={game.thumbnail_url}
          alt={game.primary_name}
          width={220}
          height={280}
          unoptimized
          className="h-64 w-full rounded-xl object-cover"
        />
      ) : (
        <div className="flex h-64 w-full items-center justify-center rounded-xl bg-[#334155] px-3 text-center text-sm text-gray-400">
          No image available
        </div>
      )}

      <h2 className="mt-3 text-center text-sm font-bold">
        {game.primary_name}
      </h2>

      <GameRating rating={game.average_rating} />

      <p className="mt-2 text-center text-xs text-gray-400">
        {item.is_played ? "Played" : "Not played yet"}
      </p>
    </Link>
  );
}

function LibraryContent({
  games,
  loading,
  error,
  query,
  activeTab,
}: {
  games: LibraryItem[];
  loading: boolean;
  error: string;
  query: string;
  activeTab: LibraryTab;
}) {
  const filteredGames = useMemo(() => {
    const search = query.trim().toLowerCase();

    return games.filter(
      (item) =>
        item.ownership === activeTab &&
        item.game.primary_name.toLowerCase().includes(search),
    );
  }, [games, query, activeTab]);

  if (loading) {
    return (
      <p className="mt-12 text-center text-gray-400">Loading your games...</p>
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

  if (filteredGames.length === 0) {
    return <EmptyLibrary query={query} activeTab={activeTab} />;
  }

  return (
    <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {filteredGames.map((item) => (
        <GameCard key={item.game.bgg_id} item={item} />
      ))}
    </div>
  );
}

function EmptyLibrary({
  query,
  activeTab,
}: {
  query: string;
  activeTab: LibraryTab;
}) {
  let message = "Your library is empty. Add some games to get started!";

  if (query.trim()) {
    message = "No games match your search.";
  } else if (activeTab === "WISHLISTED") {
    message = "Your wishlist is empty for now.";
  }

  return (
    <div className="mt-12 text-center">
      <p className="text-lg text-gray-400">{message}</p>

      {!query.trim() && (
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

export default function LibraryPage() {
  const { games, loading, error } = useLibraryGames();
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState<LibraryTab>("OWNED");

  const isWishlist = activeTab === "WISHLISTED";

  function toggleTab() {
    setActiveTab(isWishlist ? "OWNED" : "WISHLISTED");
    setQuery("");
  }

  return (
    <div className="min-h-screen bg-[#0F172A] px-8 py-10 text-white">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-5xl font-black tracking-widest">
            {isWishlist ? "WISHLIST" : "LIBRARY"}
          </h1>

          <p className="mt-2 text-gray-400">
            {isWishlist
              ? "Board games you want to add to your collection"
              : "Board games in your QuestLog collection"}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/games/search"
            className="rounded-full bg-indigo-600 px-7 py-3 text-sm font-bold uppercase tracking-wider text-white transition hover:bg-indigo-500"
          >
            + Add Game
          </Link>

          <button
            type="button"
            onClick={toggleTab}
            className="rounded-full bg-[#F87171] px-8 py-3 text-sm font-bold uppercase tracking-wider text-black transition hover:bg-[#FB7185]"
          >
            {isWishlist ? "Back to Library" : "Wishlist"}
          </button>
        </div>
      </div>

      {/* SEARCH */}
      <div className="mb-8 flex items-center gap-4">
        <input
          type="search"
          placeholder={
            isWishlist ? "Search your wishlist..." : "Search your collection..."
          }
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="w-full max-w-md rounded-full border border-gray-700 bg-[#1E293B] px-5 py-3 text-white outline-none focus:border-[#4F46E5]"
        />
      </div>

      {/* LIBRARY CONTENT */}
      <LibraryContent
        games={games}
        loading={loading}
        error={error}
        query={query}
        activeTab={activeTab}
      />
    </div>
  );
}
