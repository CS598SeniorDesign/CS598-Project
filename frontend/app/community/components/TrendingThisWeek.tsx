"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { Flame, Gamepad2, Star, Trophy } from "lucide-react";

type BoardGame = {
  bgg_id: number;
  primary_name: string;
  thumbnail_url: string | null;
  average_rating: number | string | null;
  bgg_rank: number | null;
};

type TrendingGame = {
  game: BoardGame;
  play_count: number;
  reason: "questlog_plays" | "bgg_rank";
};

const RANK_STYLES = [
  "border-yellow-400 bg-yellow-500/20 text-yellow-200 [html[data-theme=light]_&]:text-yellow-800",
  "border-border bg-gray-400/20 text-foreground",
  "border-orange-400 bg-orange-500/20 text-orange-200 [html[data-theme=light]_&]:text-orange-800",
  "border-border bg-surface-hover text-muted",
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isBoardGame(value: unknown): value is BoardGame {
  if (!isRecord(value)) return false;

  return (
    typeof value.bgg_id === "number" && typeof value.primary_name === "string"
  );
}

function isTrendingGame(value: unknown): value is TrendingGame {
  if (!isRecord(value)) return false;

  const validReason =
    value.reason === "questlog_plays" || value.reason === "bgg_rank";

  return (
    isBoardGame(value.game) &&
    typeof value.play_count === "number" &&
    validReason
  );
}

function extractTrendingGames(data: unknown): TrendingGame[] {
  if (!isRecord(data) || !Array.isArray(data.results)) {
    throw new Error("Unexpected trending games response.");
  }

  return data.results.filter(isTrendingGame);
}

function getRankStyle(index: number): string {
  return RANK_STYLES[index] ?? RANK_STYLES[3];
}

function formatRating(value: number | string | null): string | null {
  if (value == null) return null;

  const rating = Number(value);

  if (!Number.isFinite(rating)) return null;

  return rating.toFixed(1);
}

function GameCover({ game }: { game: BoardGame }) {
  const [imageFailed, setImageFailed] = useState(false);

  return (
    <div className="relative flex h-24 w-18 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border bg-surface-hover sm:h-28 sm:w-20">
      {game.thumbnail_url && !imageFailed ? (
        <Image
          src={game.thumbnail_url}
          alt={`${game.primary_name} cover`}
          fill
          unoptimized
          sizes="80px"
          className="object-cover"
          onError={() => setImageFailed(true)}
        />
      ) : (
        <Gamepad2 className="h-8 w-8 text-link" />
      )}
    </div>
  );
}

function TrendingBadge({ item }: { item: TrendingGame }) {
  if (item.reason === "questlog_plays") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-orange-500/25 bg-orange-500/10 px-2.5 py-1 text-xs font-semibold text-orange-300 [html[data-theme=light]_&]:text-orange-700">
        <Flame className="h-3 w-3" />
        {item.play_count} {item.play_count === 1 ? "play" : "plays"} this week
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-indigo-500/25 bg-indigo-500/10 px-2.5 py-1 text-xs font-semibold text-link">
      <Trophy className="h-3 w-3" />
      BGG Top Pick
    </span>
  );
}

function GameDetails({ item }: { item: TrendingGame }) {
  const rating = formatRating(item.game.average_rating);

  return (
    <div className="min-w-0 flex-1">
      <h3 className="break-words text-base font-bold text-foreground sm:text-lg">
        {item.game.primary_name}
      </h3>

      <div className="mt-2">
        <TrendingBadge item={item} />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        {item.game.bgg_rank != null && <span>BGG #{item.game.bgg_rank}</span>}

        {rating !== null && (
          <span className="inline-flex items-center gap-1">
            <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
            {rating}/10
          </span>
        )}
      </div>
    </div>
  );
}

function TrendingGameCard({
  item,
  index,
}: {
  item: TrendingGame;
  index: number;
}) {
  return (
    <article className="flex items-center gap-3 rounded-2xl border border-border bg-surface p-3 transition-all duration-300 hover:border-indigo-400/50 hover:bg-surface-hover hover:shadow-md sm:gap-4 sm:p-4">
      <div
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-sm font-bold ${getRankStyle(index)}`}
      >
        {index + 1}
      </div>

      <GameCover game={item.game} />

      <GameDetails item={item} />
    </article>
  );
}

function TrendingLoading() {
  return (
    <div role="status" className="space-y-3">
      {[1, 2, 3, 4].map((item) => (
        <div
          key={item}
          className="h-28 animate-pulse rounded-2xl border border-border bg-surface-hover"
        />
      ))}
      <span className="sr-only">Loading trending games...</span>
    </div>
  );
}

function TrendingContent({
  games,
  loading,
  error,
}: {
  games: TrendingGame[];
  loading: boolean;
  error: string;
}) {
  if (loading) return <TrendingLoading />;

  if (error) {
    return (
      <p
        role="alert"
        className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300 [html[data-theme=light]_&]:text-red-700"
      >
        {error}
      </p>
    );
  }

  if (games.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-surface p-6">
        <p className="text-lg font-semibold text-foreground">
          No trending games available
        </p>
        <p className="mt-2 text-sm text-muted">
          Games will appear here as QuestLog activity grows.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {games.map((item, index) => (
        <TrendingGameCard key={item.game.bgg_id} item={item} index={index} />
      ))}
    </div>
  );
}

export default function TrendingThisWeek() {
  const [games, setGames] = useState<TrendingGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadTrending() {
      try {
        const response = await fetch(
          "/api/v1/community/trending/?days=7&limit=4",
          {
            method: "GET",
            credentials: "same-origin",
            cache: "no-store",
            signal: controller.signal,
          },
        );

        if (response.status === 401 || response.status === 403) {
          throw new Error("Please log in to view trending games.");
        }

        if (!response.ok) {
          throw new Error("Unable to load trending games.");
        }

        const data: unknown = await response.json();
        const trending = extractTrendingGames(data);

        if (!controller.signal.aborted) {
          setGames(trending);
          setError("");
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load trending games.",
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadTrending();

    return () => controller.abort();
  }, []);

  return (
    <section className="border-t border-border pt-6">
      <div className="mb-5">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-bold tracking-wide text-foreground sm:text-3xl">
            TRENDING THIS WEEK
          </h2>
          <Flame className="h-6 w-6 text-orange-400" />
        </div>

        <p className="mt-2 text-sm text-muted">
          Popular games on QuestLog and top BoardGameGeek picks.
        </p>
      </div>

      <TrendingContent games={games} loading={loading} error={error} />
    </section>
  );
}
