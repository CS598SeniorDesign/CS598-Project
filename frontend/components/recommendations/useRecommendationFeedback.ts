"use client";

import { useEffect, useRef, useState } from "react";
import {
  fetchRecommendationFeedback,
  removeRecommendationFeedback,
  sendRecommendationFeedback,
  type Sentiment,
} from "@/lib/recommendations";

/**
 * The user's likes and dislikes, keyed by BGG ID, with an optimistic setter
 * that saves to the backend and rolls back if the save fails.
 */
export function useRecommendationFeedback() {
  const [feedback, setFeedback] = useState<Record<number, Sentiment>>({});
  const [error, setError] = useState("");
  // Mirrors `feedback` so a failed save can restore the reaction it replaced.
  const latest = useRef(feedback);

  function update(next: Record<number, Sentiment>) {
    latest.current = next;
    setFeedback(next);
  }

  function withReaction(gameId: number, sentiment: Sentiment | undefined) {
    const next = { ...latest.current };
    if (sentiment) next[gameId] = sentiment;
    else delete next[gameId];
    return next;
  }

  useEffect(() => {
    const controller = new AbortController();

    fetchRecommendationFeedback(controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return;
        const saved: Record<number, Sentiment> = Object.fromEntries(
          items.map((item) => [item.game.bgg_id, item.sentiment]),
        );
        latest.current = saved;
        setFeedback(saved);
      })
      .catch(() => {
        // Without saved feedback the buttons simply start unselected.
      });

    return () => controller.abort();
  }, []);

  async function react(
    gameId: number,
    sentiment: Sentiment | null,
    strategy?: string,
  ) {
    const previous = latest.current[gameId];
    setError("");
    update(withReaction(gameId, sentiment ?? undefined));

    try {
      if (sentiment) {
        await sendRecommendationFeedback(gameId, sentiment, strategy);
      } else {
        await removeRecommendationFeedback(gameId);
      }
    } catch (err) {
      update(withReaction(gameId, previous));
      setError(
        err instanceof Error ? err.message : "Unable to save your feedback.",
      );
    }
  }

  return { feedback, react, error };
}
