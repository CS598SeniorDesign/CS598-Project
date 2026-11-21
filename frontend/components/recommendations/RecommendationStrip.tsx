"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import ShowMoreButton from "@/app/community/components/ShowMoreButton";
import { useRecommendations } from "@/components/recommendations/useRecommendations";
import type { RecommendationQuery } from "@/lib/recommendations";

interface RecommendationStripProps {
  title: string;
  query: RecommendationQuery;
  emptyMessage?: string;
  excludeGameId?: number;
  className?: string;
  /** Opt in to collapsing the strip initially. */
  initialVisible?: number;
}

type RecommendationResponse = NonNullable<
  ReturnType<typeof useRecommendations>["response"]
>;

type RecommendationItems = RecommendationResponse["results"];

function getEligibleRecommendations(
  items: RecommendationItems | null,
  excludeGameId?: number,
): RecommendationItems {
  return (items ?? []).filter((item) => item.game.bgg_id !== excludeGameId);
}

function getVisibleRecommendations(
  eligible: RecommendationItems,
  expanded: boolean,
  collapsedCount: number,
): RecommendationItems {
  return eligible.slice(0, expanded ? eligible.length : collapsedCount);
}

export default function RecommendationStrip({
  title,
  query,
  emptyMessage = "No suggestions yet.",
  excludeGameId,
  className = "",
  initialVisible,
}: RecommendationStripProps) {
  const { response, error } = useRecommendations(query);
  const [expanded, setExpanded] = useState(false);

  const items = response?.results ?? (error ? [] : null);

  const eligible = getEligibleRecommendations(items, excludeGameId);

  const collapsedCount = initialVisible ?? eligible.length;

  const visible = getVisibleRecommendations(eligible, expanded, collapsedCount);

  const canExpand =
    !error && items !== null && eligible.length > collapsedCount;

  return (
    <section className={className} aria-label={title}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-xl font-semibold text-foreground">{title}</h2>

        <Link
          href="/recommendations"
          className="text-sm text-link hover:text-foreground"
        >
          More recommendations →
        </Link>
      </div>

      <RecommendationResults
        error={error}
        loading={items === null}
        emptyMessage={emptyMessage}
        visible={visible}
      />

      {canExpand && (
        <ShowMoreButton
          expanded={expanded}
          total={eligible.length}
          initialVisible={collapsedCount}
          onToggle={() => setExpanded((value) => !value)}
        />
      )}
    </section>
  );
}

function RecommendationResults({
  error,
  loading,
  emptyMessage,
  visible,
}: {
  error: ReturnType<typeof useRecommendations>["error"];
  loading: boolean;
  emptyMessage: string;
  visible: RecommendationItems;
}) {
  return (
    <>
      {error ? (
        <p className="text-sm text-muted">{error}</p>
      ) : loading ? (
        <p role="status" className="text-sm text-muted">
          Loading suggestions...
        </p>
      ) : visible.length === 0 ? (
        <p className="text-sm text-muted">{emptyMessage}</p>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {visible.map(({ game, reason }) => (
            <Link
              key={game.bgg_id}
              href={`/games/${game.bgg_id}`}
              className="group min-w-0 rounded-xl border border-border bg-surface p-3 text-foreground transition hover:border-indigo-400/50 hover:shadow-[0_0_20px_rgba(79,70,229,0.2)]"
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
                <div className="mb-2 flex h-28 items-center justify-center rounded-lg bg-background text-xs text-muted">
                  No image
                </div>
              )}

              <p className="truncate text-sm font-semibold text-foreground group-hover:text-link">
                {game.primary_name}
              </p>

              {reason && (
                <p className="line-clamp-2 text-xs text-muted">{reason}</p>
              )}
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
