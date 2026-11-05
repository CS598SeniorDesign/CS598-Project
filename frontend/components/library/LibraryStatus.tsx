"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  addToLibrary,
  fetchLibraryItem,
  removeFromLibrary,
  updateLibraryItem,
  type LibraryItem,
  type Ownership,
} from "@/lib/library";

const PRIMARY =
  "rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50";
const SECONDARY =
  "rounded-xl border border-indigo-500 px-6 py-3 font-semibold text-indigo-300 transition hover:bg-indigo-500/10 disabled:cursor-not-allowed disabled:opacity-50";
const DANGER =
  "rounded-xl px-4 py-3 font-semibold text-red-300 transition hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-50";

const MESSAGES: Record<Ownership, string> = {
  OWNED: "Game successfully added to your Owned library!",
  WISHLISTED: "Game successfully added to your Wishlist!",
};

function useLibraryEntry(gameId: number) {
  const [loaded, setLoaded] = useState<{
    gameId: number;
    item: LibraryItem | null;
    error: string;
  } | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchLibraryItem(gameId, controller.signal)
      .then((item) => {
        if (!controller.signal.aborted) setLoaded({ gameId, item, error: "" });
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          gameId,
          item: null,
          error:
            err instanceof Error
              ? err.message
              : "Unable to check your library.",
        });
      });

    return () => controller.abort();
  }, [gameId]);

  const current = loaded?.gameId === gameId ? loaded : null;

  return {
    checking: current === null,
    item: current?.item ?? null,
    loadError: current?.error ?? "",
    setItem: (item: LibraryItem | null) =>
      setLoaded({ gameId, item, error: "" }),
  };
}

function EntryActions({
  item,
  saving,
  onMove,
  onRemove,
}: {
  item: LibraryItem;
  saving: boolean;
  onMove: (ownership: Ownership) => void;
  onRemove: () => void;
}) {
  const owned = item.ownership === "OWNED";

  return (
    <div className="rounded-xl border border-green-700 bg-green-950/30 p-4">
      <p className="font-medium text-green-400">
        {owned ? "In your Owned library" : "On your Wishlist"}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={saving}
          onClick={() => onMove(owned ? "WISHLISTED" : "OWNED")}
          className={SECONDARY}
        >
          {owned ? "Move to Wishlist" : "Got it! Move to Owned"}
        </button>
        <button
          type="button"
          disabled={saving}
          onClick={onRemove}
          className={DANGER}
        >
          Remove
        </button>
        <Link href="/library" className="text-indigo-300 underline">
          View My Library
        </Link>
      </div>
    </div>
  );
}

/**
 * Shows whether a game is in the user's library or wishlist, with buttons to
 * add it, move it between the two, or remove it.
 */
export default function LibraryStatus({ gameId }: { gameId: number }) {
  const { checking, item, loadError, setItem } = useLibraryEntry(gameId);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function run(action: () => Promise<LibraryItem | null>, done: string) {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      setItem(await action());
      setMessage(done);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save this game.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (checking) {
    return <p className="mt-8 text-gray-400">Checking your library...</p>;
  }

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-xl font-semibold">My Library</h2>

      {item ? (
        <EntryActions
          item={item}
          saving={saving}
          onMove={(ownership) =>
            void run(
              () => updateLibraryItem(gameId, { ownership }),
              ownership === "OWNED"
                ? "Moved to your Owned library."
                : "Moved to your Wishlist.",
            )
          }
          onRemove={() =>
            void run(async () => {
              await removeFromLibrary(gameId);
              return null;
            }, "Removed from your library.")
          }
        />
      ) : (
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={saving}
            onClick={() =>
              void run(() => addToLibrary(gameId, "OWNED"), MESSAGES.OWNED)
            }
            className={PRIMARY}
          >
            {saving ? "Saving..." : "Add to Owned"}
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={() =>
              void run(
                () => addToLibrary(gameId, "WISHLISTED"),
                MESSAGES.WISHLISTED,
              )
            }
            className={SECONDARY}
          >
            {saving ? "Saving..." : "Add to Wishlist"}
          </button>
        </div>
      )}

      {message && (
        <p role="status" className="mt-3 text-green-400">
          {message}
        </p>
      )}
      {(error || loadError) && (
        <p role="alert" className="mt-3 text-red-400">
          {error || loadError}
        </p>
      )}
    </section>
  );
}
