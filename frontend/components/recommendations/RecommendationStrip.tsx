"use client";

import Image from "next/image";
import Link from "next/link";
import { useRecommendations } from "@/components/recommendations/useRecommendations";
import type { RecommendationQuery } from "@/lib/recommendations";

interface RecommendationStripProps {
  title: string;
  query: RecommendationQuery;
  /** Shown when the engine has nothing to suggest. */
  emptyMessage?: string;
  /** Leave out a game, e.g. the one whose page this strip is on. */
  excludeGameId?: number;
  className?: string;
}

/**
 * A compact row of recommendations for embedding in other pages, such as
 * "Games like this one" on a game's page or "Recommended for you" on the
 * dashboard.
 */
export default function RecommendationStrip({
  title,
  query,
  emptyMessage = "No suggestions yet.",
  excludeGameId,
  className = "",
}: RecommendationStripProps) {
  const { response, error } = useRecommendations(query);
  const items = response?.results ?? (error ? [] : null);

  const visible = (items ?? []).filter(
    (item) => item.game.bgg_id !== excludeGameId,
  );

  return (
    <section className={className} aria-label={title}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold">{title}</h2>
        <Link
          href="/recommendations"
          className="text-sm text-indigo-400 hover:text-indigo-300"
        >
          More recommendations →
        </Link>
      </div>

      {error ? (
        <p className="text-sm text-gray-400">{error}</p>
      ) : items === null ? (
        <p role="status" className="text-sm text-gray-400">
          Loading suggestions...
        </p>
      ) : visible.length === 0 ? (
        <p className="text-sm text-gray-400">{emptyMessage}</p>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {visible.map(({ game, reason }) => (
            <Link
              key={game.bgg_id}
              href={`/games/${game.bgg_id}`}
              className="group rounded-xl bg-[#0F172A] p-3 transition hover:shadow-[0_0_20px_rgba(79,70,229,0.3)]"
            >
              {game.thumbnail_url ? (
                <div className="relative mb-2 h-28 w-full">
                  <Image
                    src={game.thumbnail_url}
                    alt={game.primary_name}
                    fill
                    unoptimized
                    sizes="(max-width: 640px) 50vw, 25vw"
                    className="rounded-lg object-contain"
                  />
                </div>
              ) : (
                <div className="mb-2 flex h-28 items-center justify-center rounded-lg bg-slate-800 text-xs text-gray-400">
                  No image
                </div>
              )}
              <p className="truncate text-sm font-semibold group-hover:text-indigo-300">
                {game.primary_name}
              </p>
              {reason && (
                <p className="line-clamp-2 text-xs text-gray-400">{reason}</p>
              )}
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
