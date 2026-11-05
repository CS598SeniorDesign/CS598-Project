"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import HouseRulesEditor from "@/components/library/HouseRulesEditor";
import CardRating from "@/components/ratings/CardRating";
import {
  priorityLabel,
  WISHLIST_PRIORITIES,
  type LibraryItem,
  type LibraryItemChanges,
} from "@/lib/library";
import type { Rating } from "@/lib/ratings";

interface LibraryCardProps {
  item: LibraryItem;
  onUpdate: (gameId: number, changes: LibraryItemChanges) => Promise<unknown>;
  onRemove: (gameId: number) => Promise<void>;
  /** The user's own rating of the game, or null when they haven't rated it. */
  rating?: Rating | null;
  /** Called after the user rates the game or changes their rating. Omit to hide rating. */
  onRatingChange?: (gameId: number, rating: Rating | null) => void;
}

const BUTTON =
  "rounded-lg px-3 py-1.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-50";

function formatDate(value: string): string {
  // Dates arrive as YYYY-MM-DD; parse as local time so the day doesn't shift.
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function GameRating({ rating }: { rating: number | string | null }) {
  const numericRating = rating == null ? null : Number(rating);
  const displayRating =
    numericRating !== null && Number.isFinite(numericRating)
      ? `BGG ★ ${numericRating.toFixed(1)} / 10`
      : "Not rated on BGG";

  return (
    <p className="mt-1 text-center text-sm text-[#FACC15]">{displayRating}</p>
  );
}

export function PlayStats({ item }: { item: LibraryItem }) {
  if (item.play_count > 0) {
    const times = item.play_count === 1 ? "1 play" : `${item.play_count} plays`;
    return (
      <p className="text-center text-xs text-gray-400">
        {times}
        {item.last_played && ` · last ${formatDate(item.last_played)}`}
      </p>
    );
  }

  return (
    <p className="text-center text-xs text-gray-400">
      {item.has_played ? "Played" : "Not played yet"}
    </p>
  );
}

function CardImage({ item }: { item: LibraryItem }) {
  const { game } = item;

  return (
    <Link href={`/games/${game.bgg_id}`} className="group block">
      {game.thumbnail_url ? (
        <Image
          src={game.thumbnail_url}
          alt={game.primary_name}
          width={220}
          height={280}
          unoptimized
          className="h-56 w-full rounded-xl object-cover transition group-hover:opacity-90"
        />
      ) : (
        <div className="flex h-56 w-full items-center justify-center rounded-xl bg-[#334155] px-3 text-center text-sm text-gray-400">
          No image available
        </div>
      )}
      <h2 className="mt-3 text-center text-sm font-bold group-hover:text-indigo-300">
        {game.primary_name}
      </h2>
    </Link>
  );
}

function WishlistControls({
  item,
  busy,
  save,
}: {
  item: LibraryItem;
  busy: boolean;
  save: (changes: LibraryItemChanges) => void;
}) {
  return (
    <>
      <label className="block text-xs text-gray-400">
        Priority
        <select
          value={item.wishlist_priority ?? ""}
          disabled={busy}
          onChange={(event) =>
            save({
              wishlist_priority: event.target.value
                ? Number(event.target.value)
                : null,
            })
          }
          className="mt-1 w-full rounded-lg border border-gray-700 bg-[#0F172A] p-1.5 text-sm text-white"
        >
          <option value="">No priority</option>
          {WISHLIST_PRIORITIES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.value}. {option.label}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        disabled={busy}
        onClick={() => save({ ownership: "OWNED" })}
        className={`${BUTTON} w-full bg-emerald-600 text-white hover:bg-emerald-500`}
      >
        Got it! Move to library
      </button>
    </>
  );
}

function OwnedControls({
  item,
  busy,
  save,
}: {
  item: LibraryItem;
  busy: boolean;
  save: (changes: LibraryItemChanges) => void;
}) {
  const loggedPlays = item.play_count > 0;

  return (
    <>
      <label
        className="flex items-center gap-2 text-xs text-gray-300"
        title={
          loggedPlays
            ? "You've logged plays of this game, so it counts as played."
            : undefined
        }
      >
        <input
          type="checkbox"
          checked={item.is_played || loggedPlays}
          disabled={busy || loggedPlays}
          onChange={(event) => save({ is_played: event.target.checked })}
          className="h-4 w-4 accent-indigo-500"
        />
        I&apos;ve played this
      </label>
      <HouseRulesEditor
        gameName={item.game.primary_name}
        value={item.house_rules}
        disabled={busy}
        onSave={(houseRules) => save({ house_rules: houseRules })}
      />
      <button
        type="button"
        disabled={busy}
        onClick={() => save({ ownership: "WISHLISTED" })}
        className={`${BUTTON} w-full bg-slate-700 text-gray-200 hover:bg-slate-600`}
      >
        Move to wishlist
      </button>
    </>
  );
}

function RemoveButton({
  gameName,
  busy,
  onConfirm,
}: {
  gameName: string;
  busy: boolean;
  onConfirm: () => void;
}) {
  const [confirming, setConfirming] = useState(false);

  if (!confirming) {
    return (
      <button
        type="button"
        disabled={busy}
        onClick={() => setConfirming(true)}
        aria-label={`Remove ${gameName}`}
        className={`${BUTTON} w-full text-red-300 hover:bg-red-500/10`}
      >
        Remove
      </button>
    );
  }

  return (
    <div className="flex gap-2" role="group" aria-label={`Remove ${gameName}?`}>
      <button
        type="button"
        disabled={busy}
        onClick={onConfirm}
        className={`${BUTTON} flex-1 bg-red-600 text-white hover:bg-red-500`}
      >
        Yes, remove
      </button>
      <button
        type="button"
        onClick={() => setConfirming(false)}
        className={`${BUTTON} flex-1 bg-slate-700 text-gray-200 hover:bg-slate-600`}
      >
        Cancel
      </button>
    </div>
  );
}

/** One library or wishlist entry, with the actions that apply to it. */
export default function LibraryCard({
  item,
  onUpdate,
  onRemove,
  rating = null,
  onRatingChange,
}: LibraryCardProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const isWishlist = item.ownership === "WISHLISTED";
  const priority = isWishlist ? priorityLabel(item.wishlist_priority) : null;

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  const save = (changes: LibraryItemChanges) =>
    void run(() => onUpdate(item.game.bgg_id, changes));

  return (
    <article className="flex flex-col rounded-2xl bg-[#1E293B]/70 p-3 transition hover:shadow-xl hover:shadow-indigo-500/20">
      <CardImage item={item} />
      <GameRating rating={item.game.average_rating} />
      <PlayStats item={item} />
      {onRatingChange && (
        <div className="mt-2">
          <CardRating
            gameId={item.game.bgg_id}
            gameName={item.game.primary_name}
            rating={rating}
            onChange={onRatingChange}
          />
        </div>
      )}
      {priority && (
        <p className="mt-1 text-center text-xs font-semibold text-pink-300">
          {priority}
        </p>
      )}

      <div className="mt-3 flex flex-1 flex-col justify-end gap-2">
        {isWishlist ? (
          <WishlistControls item={item} busy={busy} save={save} />
        ) : (
          <OwnedControls item={item} busy={busy} save={save} />
        )}
        <RemoveButton
          gameName={item.game.primary_name}
          busy={busy}
          onConfirm={() => void run(() => onRemove(item.game.bgg_id))}
        />
        {error && (
          <p role="alert" className="text-xs text-red-400">
            {error}
          </p>
        )}
      </div>
    </article>
  );
}
