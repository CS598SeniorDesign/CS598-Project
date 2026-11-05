"use client";

import Link from "next/link";
import RecommendationCard from "@/components/recommendations/RecommendationCard";
import {
  FALLBACK_MESSAGES,
  type RecommendationResponse,
  type Sentiment,
} from "@/lib/recommendations";

interface RecommendationResultsProps {
  response: RecommendationResponse | null;
  loading: boolean;
  error: string;
  feedback: Record<number, Sentiment>;
  onFeedback?: (
    gameId: number,
    sentiment: Sentiment | null,
    strategy: string,
  ) => void;
  emptyMessage?: string;
  /** Called when the user follows the fallback notice to their preferences. */
  onOpenPreferences?: () => void;
}

function ResultsStatus({
  loading,
  error,
}: {
  loading: boolean;
  error: string;
}) {
  if (loading) {
    return (
      <p role="status" className="mt-8 text-center text-gray-400">
        Finding games for you...
      </p>
    );
  }

  return (
    <div className="mt-8 text-center">
      <p role="alert" className="text-red-400">
        {error}
      </p>
      {error.startsWith("Please log in") && (
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

function FallbackNotice({
  reason,
  onOpenPreferences,
}: {
  reason: string | null;
  onOpenPreferences?: () => void;
}) {
  if (!reason) return null;

  return (
    <div
      role="note"
      className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-600/60 bg-amber-950/30 p-4 text-amber-200"
    >
      <span>{FALLBACK_MESSAGES[reason] ?? reason}</span>
      {reason === "opt_in_required" && onOpenPreferences && (
        <button
          type="button"
          onClick={onOpenPreferences}
          className="rounded-lg bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-500"
        >
          Open Preferences
        </button>
      )}
    </div>
  );
}

/**
 * A grid of recommended games, plus a notice when the backend fell back to a
 * basic strategy. Games the user has disliked are hidden straight away, since
 * the backend stops recommending them.
 */
export default function RecommendationResults({
  response,
  loading,
  error,
  feedback,
  onFeedback,
  emptyMessage = "No games match yet. Try loosening your filters.",
  onOpenPreferences,
}: RecommendationResultsProps) {
  if (loading || error) {
    return <ResultsStatus loading={loading} error={error} />;
  }

  if (!response) return null;

  const visible = response.results.filter(
    (item) => feedback[item.game.bgg_id] !== "DISLIKE",
  );
  const cardFeedback =
    onFeedback &&
    ((gameId: number, sentiment: Sentiment | null) =>
      onFeedback(gameId, sentiment, response.strategy));

  return (
    <div className="mt-6">
      <FallbackNotice
        reason={response.fallback_reason}
        onOpenPreferences={onOpenPreferences}
      />

      {response.personalized && (
        <p className="mb-4 text-sm text-emerald-300">
          ✨ Personalized from your plays, library and likes
        </p>
      )}

      {visible.length === 0 ? (
        <p className="mt-8 text-center text-gray-400">{emptyMessage}</p>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {visible.map((item) => (
            <RecommendationCard
              key={item.game.bgg_id}
              recommendation={item}
              sentiment={feedback[item.game.bgg_id]}
              onFeedback={cardFeedback}
            />
          ))}
        </div>
      )}
    </div>
  );
}
