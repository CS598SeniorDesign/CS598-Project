"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import Link from "next/link";
import Image from "next/image";

interface Game {
  bgg_id: number;
  primary_name: string;
  year_published: number | null;
  thumbnail_url: string | null;
  average_rating: number | string | null;
  bgg_rank: number | null;
}

interface SubmittedSearch {
  query: string;
  id: number;
}

interface GameResultsProps {
  games: Game[];
  loading: boolean;
  error: string;
  submittedSearch: SubmittedSearch | null;
}

function getCatalogError(status: number): string {
  if (status === 401 || status === 403) {
    return "Please log in to search for games.";
  }

  return "Unable to load games. Please try again.";
}

function parseGames(data: unknown): Game[] {
  if (Array.isArray(data)) {
    return data as Game[];
  }

  if (
    data !== null &&
    typeof data === "object" &&
    "results" in data &&
    Array.isArray(data.results)
  ) {
    return data.results as Game[];
  }

  throw new Error("Unexpected response from the game catalog.");
}

async function fetchGames(
  searchQuery: string,
  signal: AbortSignal,
): Promise<Game[]> {
  const params = new URLSearchParams({
    search: searchQuery,
  });

  const response = await fetch(`/api/v1/games/?${params.toString()}`, {
    credentials: "same-origin",
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error(getCatalogError(response.status));
  }

  const data: unknown = await response.json();
  return parseGames(data);
}

function GameCard({ game }: { game: Game }) {
  return (
    <Link
      href={`/games/${game.bgg_id}`}
      className="rounded-2xl bg-gray-900 p-4 shadow-lg transition duration-300 hover:scale-105 hover:shadow-indigo-500/20"
    >
      {game.thumbnail_url ? (
        <div className="relative mb-3 h-40 w-full">
          <Image
            src={game.thumbnail_url}
            alt={game.primary_name}
            fill
            unoptimized
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
            className="rounded-lg object-contain"
          />
        </div>
      ) : (
        <div className="mb-3 flex h-40 items-center justify-center rounded-lg bg-slate-800 text-gray-400">
          No image available
        </div>
      )}

      <h2 className="text-lg font-semibold">{game.primary_name}</h2>

      <p className="text-sm text-gray-400">
        {game.year_published ?? "Year unknown"}
      </p>

      {game.average_rating != null && (
        <p className="mt-2 text-sm text-gray-300">
          BGG Rating: {Number(game.average_rating).toFixed(1)}
        </p>
      )}
    </Link>
  );
}

function GameResults({
  games,
  loading,
  error,
  submittedSearch,
}: GameResultsProps) {
  if (!submittedSearch) {
    return (
      <div className="mt-16 text-center">
        <p className="text-xl font-semibold text-gray-200">
          Ready to find your next favorite game?
        </p>
        <p className="mt-3 text-gray-400">
          Search for a board game to explore titles available in the QuestLog
          catalog.
        </p>
      </div>
    );
  }

  if (loading) {
    return <p className="mt-10 text-center text-gray-400">Loading games...</p>;
  }

  if (error) {
    return (
      <div className="mt-10 text-center">
        <p role="alert" className="text-red-400">
          {error}
        </p>

        {error === "Please log in to search for games." && (
          <Link
            href="/login"
            className="mt-3 inline-block text-indigo-400 hover:text-indigo-300"
          >
            Go to Login
          </Link>
        )}
      </div>
    );
  }

  if (games.length === 0) {
    return (
      <p className="mt-10 text-center text-gray-400">
        No games found in the catalog for &quot;{submittedSearch.query}&quot;.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {games.map((game) => (
        <GameCard key={game.bgg_id} game={game} />
      ))}
    </div>
  );
}

export default function GameSearchPage() {
  const [query, setQuery] = useState("");
  const [games, setGames] = useState<Game[]>([]);
  const [submittedSearch, setSubmittedSearch] =
    useState<SubmittedSearch | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!submittedSearch) {
      return;
    }

    const controller = new AbortController();
    const searchTerm = submittedSearch.query;

    async function loadGames() {
      setLoading(true);
      setError("");

      try {
        const results = await fetchGames(searchTerm, controller.signal);

        if (!controller.signal.aborted) {
          setGames(results);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

        setGames([]);
        setError(err instanceof Error ? err.message : "Something went wrong.");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadGames();

    return () => controller.abort();
  }, [submittedSearch]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const searchTerm = query.trim();

    if (!searchTerm) {
      return;
    }

    setGames([]);
    setError("");
    setLoading(true);

    setSubmittedSearch((previous) => ({
      query: searchTerm,
      id: (previous?.id ?? 0) + 1,
    }));
  }

  function handleClear() {
    setQuery("");
    setSubmittedSearch(null);
    setGames([]);
    setError("");
    setLoading(false);
  }

  return (
    <main className="min-h-screen bg-[#0F172A] p-8 text-[#F8FAFC]">
      <h1 className="mb-2 text-3xl font-bold">Game Search</h1>

      <p className="mb-6 text-gray-400">Find your next favorite game</p>

      <form onSubmit={handleSearch} className="mb-8 flex gap-4">
        <input
          type="search"
          placeholder="Search games..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="w-full rounded-2xl border border-gray-700 bg-gray-900 p-4 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />

        <button
          type="submit"
          disabled={!query.trim()}
          className="rounded-xl bg-indigo-600 px-6 transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Search
        </button>

        {(query || submittedSearch) && (
          <button
            type="button"
            onClick={handleClear}
            className="rounded-xl bg-gray-700 px-4 transition hover:bg-gray-600"
          >
            Clear
          </button>
        )}
      </form>

      <GameResults
        games={games}
        loading={loading}
        error={error}
        submittedSearch={submittedSearch}
      />
    </main>
  );
}
