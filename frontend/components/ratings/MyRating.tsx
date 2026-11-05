"use client";

import { useEffect, useState } from "react";
import RatingEditor from "@/components/ratings/RatingEditor";
import {
  fetchRating,
  formatOverall,
  RATING_DIMENSIONS,
  type Rating,
} from "@/lib/ratings";

interface Loaded {
  gameId: number;
  rating: Rating | null;
  error: string;
}

function useMyRating(gameId: number) {
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchRating(gameId, controller.signal)
      .then((rating) => {
        if (!controller.signal.aborted) {
          setLoaded({ gameId, rating, error: "" });
        }
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          gameId,
          rating: null,
          error:
            err instanceof Error ? err.message : "Unable to load your rating.",
        });
      });

    return () => controller.abort();
  }, [gameId]);

  const current = loaded?.gameId === gameId ? loaded : null;

  return {
    loading: current === null,
    rating: current?.rating ?? null,
    error: current?.error ?? "",
    setRating: (rating: Rating | null) =>
      setLoaded({ gameId, rating, error: "" }),
  };
}

function RatingSummary({ rating }: { rating: Rating }) {
  return (
    <div>
      <p className="text-2xl font-bold text-[#FACC15]">
        ★ {formatOverall(rating.overall_rating)}{" "}
        <span className="text-base font-normal text-gray-400">/ 5 overall</span>
      </p>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
        {RATING_DIMENSIONS.map((dimension) => (
          <div key={dimension.key}>
            <dt className="text-gray-400">{dimension.label}</dt>
            <dd className="font-semibold">{rating[dimension.key]} / 5</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

/** The user's own rating of a game, with a form to add, change or delete it. */
export default function MyRating({
  gameId,
  gameName,
}: {
  gameId: number;
  gameName: string;
}) {
  const { loading, rating, error, setRating } = useMyRating(gameId);
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState("");

  if (loading) {
    return <p className="mt-8 text-gray-400">Loading your rating...</p>;
  }

  return (
    <section className="mt-8" aria-label="Your rating">
      <h2 className="mb-3 text-xl font-semibold">Your Rating</h2>

      <div className="rounded-xl bg-gray-900 p-4">
        {editing ? (
          <RatingEditor
            gameId={gameId}
            gameName={gameName}
            rating={rating}
            onSaved={(saved) => {
              setRating(saved);
              setEditing(false);
              setMessage(saved ? "Rating saved." : "Rating deleted.");
            }}
            onCancel={() => setEditing(false)}
          />
        ) : (
          <>
            {rating ? (
              <RatingSummary rating={rating} />
            ) : (
              <p className="text-gray-400">
                You haven&apos;t rated this game yet.
              </p>
            )}
            <button
              type="button"
              onClick={() => {
                setMessage("");
                setEditing(true);
              }}
              className="mt-4 rounded-xl border border-indigo-500 px-5 py-2 font-semibold text-indigo-300 transition hover:bg-indigo-500/10"
            >
              {rating ? "Edit rating" : "Rate this game"}
            </button>
          </>
        )}
      </div>

      {message && (
        <p role="status" className="mt-3 text-green-400">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-3 text-red-400">
          {error}
        </p>
      )}
    </section>
  );
}
