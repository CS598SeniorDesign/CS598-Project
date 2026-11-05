"use client";

import { useEffect, useState } from "react";
import {
  fetchRecommendations,
  type RecommendationQuery,
  type RecommendationResponse,
} from "@/lib/recommendations";

interface Loaded {
  key: string;
  response: RecommendationResponse | null;
  error: string;
}

/**
 * Load recommendations whenever `query` changes, cancelling any request still
 * in flight. A null query loads nothing.
 *
 * Results are stored with the query they answer, so a stale answer is never
 * shown for a newer query and `loading` needs no state of its own.
 */
export function useRecommendations(query: RecommendationQuery | null) {
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const queryKey = query ? JSON.stringify(query) : null;

  useEffect(() => {
    if (!queryKey) return;

    const controller = new AbortController();

    fetchRecommendations(JSON.parse(queryKey), controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;
        setLoaded({ key: queryKey, response, error: "" });
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          key: queryKey,
          response: null,
          error:
            err instanceof Error
              ? err.message
              : "Unable to load recommendations.",
        });
      });

    return () => controller.abort();
  }, [queryKey]);

  const current = queryKey !== null && loaded?.key === queryKey;

  return {
    response: current ? loaded.response : null,
    error: current ? loaded.error : "",
    loading: queryKey !== null && !current,
  };
}
