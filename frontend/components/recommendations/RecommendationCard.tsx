"use client";

import Image from "next/image";
import Link from "next/link";
import type { Recommendation, Sentiment } from "@/lib/recommendations";

interface RecommendationCardProps {
  recommendation: Recommendation;
  sentiment?: Sentiment;
  /** Called with the new reaction, or null to clear it. Omit to hide the buttons. */
  onFeedback?: (gameId: number, sentiment: Sentiment | null) => void;
  disabled?: boolean;
}

export default function RecommendationCard({
  recommendation,
  sentiment,
  onFeedback,
  disabled = false,
}: RecommendationCardProps) {
  const { game, reason } = recommendation;

  function toggle(choice: Sentiment) {
    onFeedback?.(game.bgg_id, sentiment === choice ? null : choice);
  }

  return (
    <article className="flex flex-col rounded-2xl bg-gray-900 p-4 shadow-lg transition duration-300 hover:shadow-indigo-500/20">
      <Link href={`/games/${game.bgg_id}`} className="group flex-1">
        {game.thumbnail_url ? (
          <div className="relative mb-3 h-40 w-full">
            <Image
              src={game.thumbnail_url}
              alt={game.primary_name}
              fill
              unoptimized
              sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
              className="rounded-lg object-contain transition group-hover:scale-105"
            />
          </div>
        ) : (
          <div className="mb-3 flex h-40 items-center justify-center rounded-lg bg-slate-800 text-gray-400">
            No image available
          </div>
        )}

        <h3 className="text-lg font-semibold group-hover:text-indigo-300">
          {game.primary_name}
        </h3>
        <p className="text-sm text-gray-400">
          {game.year_published ?? "Year unknown"}
          {game.average_rating != null &&
            ` · BGG ${Number(game.average_rating).toFixed(1)}`}
        </p>
        {reason && <p className="mt-2 text-sm text-indigo-200">{reason}</p>}
      </Link>

      {onFeedback && (
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            disabled={disabled}
            aria-pressed={sentiment === "LIKE"}
            aria-label={`Like ${game.primary_name}`}
            onClick={() => toggle("LIKE")}
            className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${
              sentiment === "LIKE"
                ? "bg-emerald-600 text-white"
                : "bg-slate-800 text-gray-300 hover:bg-slate-700"
            }`}
          >
            👍 {sentiment === "LIKE" ? "Liked" : "Like"}
          </button>
          <button
            type="button"
            disabled={disabled}
            aria-pressed={sentiment === "DISLIKE"}
            aria-label={`Not interested in ${game.primary_name}`}
            onClick={() => toggle("DISLIKE")}
            className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${
              sentiment === "DISLIKE"
                ? "bg-red-600 text-white"
                : "bg-slate-800 text-gray-300 hover:bg-slate-700"
            }`}
          >
            👎 Not for me
          </button>
        </div>
      )}
    </article>
  );
}
