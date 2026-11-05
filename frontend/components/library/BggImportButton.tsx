"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  fetchBggCollectionSyncStatus,
  FINISHED_SYNC_STATES,
  startBggCollectionSync,
  type SyncStatus,
} from "@/lib/library";

/** How often to check on a running import, in milliseconds. */
export const SYNC_POLL_INTERVAL = 2000;

interface BggImportButtonProps {
  /** Called once an import succeeds, to reload the library. */
  onImported: () => void;
}

function resultMessage(status: SyncStatus): string {
  if (status.status !== "succeeded") return status.detail;

  const parts = [
    `${status.added ?? 0} added`,
    `${status.updated ?? 0} updated`,
    `${status.skipped ?? 0} skipped`,
  ];
  return `Import finished: ${parts.join(", ")}.`;
}

/**
 * Imports the games the user owns or wishlists on BoardGameGeek. The import
 * runs in the background, so this polls its status until it finishes.
 */
export default function BggImportButton({ onImported }: BggImportButtonProps) {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);
  // Read through a ref so a new callback from the parent doesn't restart polling.
  const onImportedRef = useRef(onImported);

  useEffect(() => {
    onImportedRef.current = onImported;
  }, [onImported]);

  useEffect(() => {
    if (!taskId) return;

    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll(id: string) {
      try {
        const next = await fetchBggCollectionSyncStatus(id, controller.signal);
        if (controller.signal.aborted) return;
        setStatus(next);

        if (!FINISHED_SYNC_STATES.has(next.status)) {
          timer = setTimeout(() => void poll(id), SYNC_POLL_INTERVAL);
          return;
        }
        setTaskId(null);
        if (next.status === "succeeded") onImportedRef.current();
      } catch (err) {
        if (controller.signal.aborted) return;
        setTaskId(null);
        setError(
          err instanceof Error ? err.message : "Unable to check the import.",
        );
      }
    }

    timer = setTimeout(() => void poll(taskId), SYNC_POLL_INTERVAL);

    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [taskId]);

  async function start() {
    setStarting(true);
    setError("");
    setStatus(null);

    try {
      const queued = await startBggCollectionSync();
      setStatus(queued);
      setTaskId(queued.task_id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to start the import.",
      );
    } finally {
      setStarting(false);
    }
  }

  const running = starting || taskId !== null;
  const needsUsername = /username/i.test(error);

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={() => void start()}
        disabled={running}
        className="rounded-full border border-indigo-400 px-6 py-3 text-sm font-bold uppercase tracking-wider text-indigo-200 transition hover:bg-indigo-500/10 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {running ? "Importing..." : "Import from BGG"}
      </button>

      {status && !error && (
        <p
          role="status"
          className={`max-w-xs text-right text-xs ${
            status.status === "failed" ? "text-red-400" : "text-gray-400"
          }`}
        >
          {resultMessage(status)}
        </p>
      )}

      {error && (
        <p role="alert" className="max-w-xs text-right text-xs text-red-400">
          {error}{" "}
          {needsUsername && (
            <Link href="/profile/edit" className="underline">
              Add your BGG username
            </Link>
          )}
        </p>
      )}
    </div>
  );
}
