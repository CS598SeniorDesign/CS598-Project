"use client";

import { useEffect, useState } from "react";
import { fetchRatings, type Rating } from "@/lib/ratings";

/**
 * All of the user's ratings keyed by BGG ID, loaded once, with a setter to
 * apply a rating saved or deleted elsewhere on the page.
 */
export function useRatings() {
  const [ratings, setRatings] = useState<Record<number, Rating>>({});

  useEffect(() => {
    const controller = new AbortController();

    fetchRatings(controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return;
        setRatings(
          Object.fromEntries(items.map((item) => [item.game.bgg_id, item])),
        );
      })
      .catch(() => {
        // Without ratings the cards just offer to rate each game.
      });

    return () => controller.abort();
  }, []);

  function setRating(gameId: number, rating: Rating | null) {
    setRatings((current) => {
      const next = { ...current };
      if (rating) next[gameId] = rating;
      else delete next[gameId];
      return next;
    });
  }

  return { ratings, setRating };
}
