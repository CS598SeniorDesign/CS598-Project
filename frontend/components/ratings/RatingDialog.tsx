"use client";

import { useEffect, useRef } from "react";
import RatingEditor from "@/components/ratings/RatingEditor";
import type { Rating } from "@/lib/ratings";

interface RatingDialogProps {
  gameId: number;
  gameName: string;
  rating: Rating | null;
  onSaved: (rating: Rating | null) => void;
  onClose: () => void;
}

/**
 * The rating editor in a modal dialog, for places without room for it inline
 * such as library cards. Uses the native <dialog>, which traps focus and
 * closes on Escape.
 */
export default function RatingDialog({
  gameId,
  gameName,
  rating,
  onSaved,
  onClose,
}: RatingDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    // jsdom has no showModal; fall back to a plain open dialog there.
    if (dialog && !dialog.open) {
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
    }
  }, []);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={`rating-dialog-${gameId}`}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      className="w-full max-w-md rounded-2xl bg-[#1E293B] p-6 text-white backdrop:bg-black/60"
    >
      <h2 id={`rating-dialog-${gameId}`} className="mb-4 text-xl font-bold">
        {rating ? "Edit your rating of" : "Rate"} {gameName}
      </h2>
      <RatingEditor
        gameId={gameId}
        gameName={gameName}
        rating={rating}
        onSaved={(saved) => {
          onSaved(saved);
          onClose();
        }}
        onCancel={onClose}
      />
    </dialog>
  );
}
