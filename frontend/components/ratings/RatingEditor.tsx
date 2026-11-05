"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import StarInput from "@/components/ratings/StarInput";
import {
  deleteRating,
  formatOverall,
  RATING_DIMENSIONS,
  saveRating,
  type Rating,
  type RatingDimension,
  type RatingScores,
} from "@/lib/ratings";

interface RatingEditorProps {
  gameId: number;
  gameName: string;
  /** The user's current rating, or null to create one. */
  rating: Rating | null;
  /** Called with the saved rating, or null after it is deleted. */
  onSaved: (rating: Rating | null) => void;
  onCancel?: () => void;
}

type Draft = Record<RatingDimension, number>;

function initialDraft(rating: Rating | null): Draft {
  return {
    experience: rating?.experience ?? 0,
    mechanics: rating?.mechanics ?? 0,
    replayability: rating?.replayability ?? 0,
    enjoyment: rating?.enjoyment ?? 0,
  };
}

function isComplete(draft: Draft): draft is RatingScores {
  return Object.values(draft).every((score) => score > 0);
}

function average(draft: Draft): number | null {
  if (!isComplete(draft)) return null;
  const scores = Object.values(draft);
  return scores.reduce((total, score) => total + score, 0) / scores.length;
}

/** Rate a game on each dimension, or change or delete an existing rating. */
export default function RatingEditor({
  gameId,
  gameName,
  rating,
  onSaved,
  onCancel,
}: RatingEditorProps) {
  const [draft, setDraft] = useState<Draft>(() => initialDraft(rating));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const overall = average(draft);

  async function run(action: () => Promise<Rating | null>) {
    setBusy(true);
    setError("");
    try {
      onSaved(await action());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isComplete(draft)) return;
    void run(() => saveRating(gameId, draft, rating !== null));
  }

  function handleDelete() {
    void run(async () => {
      await deleteRating(gameId);
      return null;
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      aria-label={`Your rating for ${gameName}`}
      className="space-y-4"
    >
      {RATING_DIMENSIONS.map((dimension) => (
        <StarInput
          key={dimension.key}
          label={dimension.label}
          hint={dimension.hint}
          value={draft[dimension.key]}
          disabled={busy}
          onChange={(score) =>
            setDraft((current) => ({ ...current, [dimension.key]: score }))
          }
        />
      ))}

      <p className="text-sm text-gray-300">
        Overall:{" "}
        <span className="font-semibold text-[#FACC15]">
          {overall === null
            ? "Pick a score for each"
            : `★ ${formatOverall(overall)} / 5`}
        </span>
      </p>

      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={busy || overall === null}
          className="rounded-xl bg-indigo-600 px-5 py-2 font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Saving..." : "Save rating"}
        </button>
        {rating && (
          <button
            type="button"
            disabled={busy}
            onClick={handleDelete}
            className="rounded-xl px-4 py-2 font-semibold text-red-300 transition hover:bg-red-500/10 disabled:opacity-50"
          >
            Delete rating
          </button>
        )}
        {onCancel && (
          <button
            type="button"
            disabled={busy}
            onClick={onCancel}
            className="rounded-xl bg-slate-700 px-4 py-2 font-semibold text-gray-200 transition hover:bg-slate-600"
          >
            Cancel
          </button>
        )}
      </div>

      {error && (
        <p role="alert" className="text-sm text-red-400">
          {error}
        </p>
      )}
    </form>
  );
}
