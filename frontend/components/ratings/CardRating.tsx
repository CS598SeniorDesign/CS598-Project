"use client";

import { useState } from "react";
import RatingDialog from "@/components/ratings/RatingDialog";
import { formatOverall, type Rating } from "@/lib/ratings";

interface CardRatingProps {
  gameId: number;
  gameName: string;
  rating: Rating | null;
  onChange: (gameId: number, rating: Rating | null) => void;
}

/** The user's overall rating on a game card, with a button to rate or edit. */
export default function CardRating({
  gameId,
  gameName,
  rating,
  onChange,
}: CardRatingProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex items-center justify-between gap-2 text-xs">
      <span
        className={rating ? "font-semibold text-[#FACC15]" : "text-gray-400"}
      >
        {rating
          ? `Your rating ★ ${formatOverall(rating.overall_rating)} / 5`
          : "Not rated by you"}
      </span>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={`${rating ? "Edit your rating of" : "Rate"} ${gameName}`}
        className="font-semibold text-indigo-300 hover:text-indigo-200"
      >
        {rating ? "Edit" : "Rate"}
      </button>

      {open && (
        <RatingDialog
          gameId={gameId}
          gameName={gameName}
          rating={rating}
          onSaved={(saved) => onChange(gameId, saved)}
          onClose={() => setOpen(false)}
        />
      )}
    </div>
  );
}
