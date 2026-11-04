"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

type BoardGame = {
  bgg_id: number;
  primary_name: string;
  thumbnail_url: string | null;
  average_rating: number | null;
  bgg_rank: number | null;
};

function isBoardGame(value: unknown): value is BoardGame {
  return (
    typeof value === "object" &&
    value !== null &&
    "bgg_id" in value &&
    typeof value.bgg_id === "number" &&
    "primary_name" in value &&
    typeof value.primary_name === "string"
  );
}

function extractGames(data: unknown): unknown[] {
  if (Array.isArray(data)) {
    return data;
  }

  if (
    typeof data === "object" &&
    data !== null &&
    "results" in data &&
    Array.isArray(data.results)
  ) {
    return data.results;
  }

  throw new Error("Unexpected catalog response.");
}

function getFeaturedGames(data: unknown[]): BoardGame[] {
  return data
    .filter(isBoardGame)
    .sort(
      (a, b) =>
        (a.bgg_rank ?? Number.MAX_SAFE_INTEGER) -
        (b.bgg_rank ?? Number.MAX_SAFE_INTEGER),
    )
    .slice(0, 4);
}

function getRankStyle(index: number): string {
  const styles = [
    "bg-yellow-500/20 border-yellow-400",
    "bg-gray-400/20 border-gray-300",
    "bg-orange-500/20 border-orange-400",
    "bg-zinc-800 border-gray-600",
  ];

  return styles[index] ?? styles[3];
}

function GameCover({ game }: { game: BoardGame }) {
  const [imageFailed, setImageFailed] = useState(false);

  return (
    <div className="relative flex h-28 w-20 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-gray-600 bg-slate-800">
      {game.thumbnail_url && !imageFailed ? (
        <Image
          src={game.thumbnail_url}
          alt={`${game.primary_name} cover`}
          fill
          unoptimized
          className="object-cover"
          onError={() => setImageFailed(true)}
        />
      ) : (
        <span className="text-3xl" aria-hidden="true">
          🎲
        </span>
      )}
    </div>
  );
}

export default function TrendingThisWeek() {
  const [games, setGames] = useState<BoardGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadGames() {
      try {
        const response = await fetch("/api/v1/games/", {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error("Unable to load featured games.");
        }

        const data: unknown = await response.json();
        const featured = getFeaturedGames(extractGames(data));

        if (!controller.signal.aborted) {
          setGames(featured);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load featured games.",
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadGames();

    return () => controller.abort();
  }, []);

  return (
    <section className="border-t border-gray-600 pt-6">
      <h2 className="mb-2 text-3xl font-bold tracking-wide">
        FEATURED GAMES 🎲
      </h2>

      <p className="mb-5 text-sm text-gray-400">
        Discover games from the QuestLog catalog
      </p>

      {loading && <p className="text-gray-400">Loading featured games...</p>}

      {!loading && error && (
        <p role="alert" className="text-red-400">
          {error}
        </p>
      )}

      {!loading && !error && games.length === 0 && (
        <div className="rounded-xl border border-gray-700 bg-slate-800/40 p-6">
          <p className="text-lg font-semibold">No featured games available</p>

          <p className="mt-2 text-sm text-gray-400">
            Games will appear here once they are added to the QuestLog catalog.
          </p>
        </div>
      )}

      {!loading && !error && games.length > 0 && (
        <div className="space-y-5">
          {games.map((game, index) => (
            <div
              key={game.bgg_id}
              className="flex items-center gap-5 rounded-2xl border border-gray-700 bg-zinc-900 p-4 transition hover:scale-[1.02] hover:border-gray-400"
            >
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border text-lg font-bold text-white ${getRankStyle(index)}`}
              >
                {index + 1}
              </div>

              <GameCover game={game} />

              <div className="min-w-0">
                <p className="text-xl font-semibold sm:text-2xl">
                  {game.primary_name}
                </p>

                <div className="mt-2 space-y-1 text-sm text-gray-400">
                  {game.bgg_rank != null && <p>BGG Rank: #{game.bgg_rank}</p>}

                  {game.average_rating != null && (
                    <p>
                      ⭐ {Number(game.average_rating).toFixed(1)}
                      /10 on BGG
                    </p>
                  )}

                  {game.bgg_rank == null && game.average_rating == null && (
                    <p>Available in QuestLog</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
