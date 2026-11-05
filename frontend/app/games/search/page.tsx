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

interface BggSearchResult {
  bgg_id: number;
  item_type: string;
  name: string;
  is_primary_name: boolean;
  year_published: number | null;
  is_in_catalog: boolean;
  thumbnail_url: string | null;
}

interface BggSearchResponse {
  query: string;
  total_matches: number;
  results: BggSearchResult[];
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

  if (status === 400) {
    return "Please enter a valid game name between 2 and 100 characters.";
  }

  if (status === 429) {
    return "Too many searches. Please wait a moment and try again.";
  }

  if (status === 502) {
    return "BoardGameGeek is temporarily unavailable. Please try again later.";
  }

  return "Unable to load games. Please try again.";
}

function isBggSearchResult(value: unknown): value is BggSearchResult {
  if (value === null || typeof value !== "object") {
    return false;
  }

  const game = value as Partial<BggSearchResult>;

  return (
    typeof game.bgg_id === "number" &&
    typeof game.name === "string" &&
    (game.year_published === null || typeof game.year_published === "number") &&
    (game.thumbnail_url === null || typeof game.thumbnail_url === "string")
  );
}

function parseBggSearchResponse(data: unknown): BggSearchResponse {
  if (data === null || typeof data !== "object") {
    throw new Error("Unexpected response from BGG search.");
  }

  const response = data as Partial<BggSearchResponse>;

  if (
    !Array.isArray(response.results) ||
    !response.results.every(isBggSearchResult)
  ) {
    throw new Error("Unexpected response from BGG search.");
  }

  return response as BggSearchResponse;
}

function mapBggGame(game: BggSearchResult): Game {
  return {
    bgg_id: game.bgg_id,
    primary_name: game.name,
    year_published: game.year_published,
    thumbnail_url: game.thumbnail_url,
    average_rating: null,
    bgg_rank: null,
  };
}

async function fetchGames(
  searchQuery: string,
  signal: AbortSignal,
): Promise<Game[]> {
  const params = new URLSearchParams({
    query: searchQuery,
  });

  const response = await fetch(`/api/v1/games/search/?${params.toString()}`, {
    credentials: "same-origin",
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error(getCatalogError(response.status));
  }

  const data: unknown = await response.json();
  const searchResponse = parseBggSearchResponse(data);

  return searchResponse.results.map(mapBggGame);
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
          Search for a board game to explore titles available through
          BoardGameGeek.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <p className="mt-10 text-center text-gray-400">
        Searching BoardGameGeek...
      </p>
    );
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
        No games found for &quot;{submittedSearch.query}&quot;.
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
        if (controller.signal.aborted) {
          return;
        }

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

    const searchTerm = query.trim().replace(/\s+/g, " ");

    if (searchTerm.length < 2 || searchTerm.length > 100) {
      setError("Please enter between 2 and 100 characters.");
      setGames([]);
      setSubmittedSearch(null);
      setLoading(false);
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

  const trimmedQuery = query.trim().replace(/\s+/g, " ");
  const isValidQuery = trimmedQuery.length >= 2 && trimmedQuery.length <= 100;

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
          maxLength={100}
          aria-label="Search board games"
          className="w-full rounded-2xl border border-gray-700 bg-gray-900 p-4 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />

        <button
          type="submit"
          disabled={!isValidQuery}
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

      {!submittedSearch && error && (
        <p role="alert" className="mb-4 text-red-400">
          {error}
        </p>
      )}

      <GameResults
        games={games}
        loading={loading}
        error={error}
        submittedSearch={submittedSearch}
      />
    </main>
  );
}
