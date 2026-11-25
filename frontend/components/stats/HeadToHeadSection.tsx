"use client";

import { useEffect, useState } from "react";
import { Gamepad2 } from "lucide-react";
import {
  fetchHeadToHead,
  formatPlayDate,
  formatWinRate,
  type HeadToHead,
} from "@/lib/analytics";

interface HeadToHeadResult {
  userId: string;
  record: HeadToHead | null;
  error: string;
}

/**
 * Load the record against a player. The result is kept with the user ID it
 * was loaded for, so switching players shows loading until the new one lands.
 */
function useHeadToHead(userId: string) {
  const [result, setResult] = useState<HeadToHeadResult | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchHeadToHead(userId, controller.signal)
      .then((record) => {
        if (!controller.signal.aborted) {
          setResult({ userId, record, error: "" });
        }
      })
      .catch((caughtError: unknown) => {
        if (!controller.signal.aborted) {
          setResult({
            userId,
            record: null,
            error:
              caughtError instanceof Error
                ? caughtError.message
                : "Unable to load statistics. Please try again.",
          });
        }
      });

    return () => controller.abort();
  }, [userId]);

  return result?.userId === userId ? result : null;
}

function StatTile({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-background p-5 text-center">
      <p className="mb-2 text-sm text-muted">{label}</p>

      <p className="text-2xl font-bold text-link">{value}</p>

      {detail && <p className="mt-2 text-xs text-muted">{detail}</p>}
    </div>
  );
}

function HeadToHeadRecord({
  record,
  friendName,
}: {
  record: HeadToHead;
  friendName: string;
}) {
  const plays =
    record.plays_together === record.sessions_together
      ? undefined
      : `${record.plays_together} plays`;

  return (
    <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile
          label="You won"
          value={record.you_won}
          detail={`${formatWinRate(record.your_win_rate)} win rate`}
        />

        <StatTile
          label={`${friendName} won`}
          value={record.they_won}
          detail={`${formatWinRate(record.their_win_rate)} win rate`}
        />

        <StatTile label="Won together" value={record.both_won} />

        <StatTile label="Neither won" value={record.neither_won} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <StatTile
          label="Games together"
          value={record.sessions_together}
          detail={plays}
        />

        <StatTile
          label="Last played"
          value={
            record.last_played ? formatPlayDate(record.last_played) : "N/A"
          }
        />
      </div>

      {record.games.length > 0 && (
        <div className="mt-6">
          <h3 className="mb-3 font-semibold text-foreground">
            Games You Play Together
          </h3>

          <ul className="space-y-3">
            {record.games.map((game) => (
              <li
                key={game.bgg_id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-background p-4 text-foreground transition hover:bg-surface-hover"
              >
                <div>
                  <p className="font-semibold text-foreground">{game.name}</p>

                  <p className="text-sm text-muted">
                    {game.sessions} {game.sessions === 1 ? "game" : "games"}
                  </p>
                </div>

                <p className="text-sm text-subtle">
                  You{" "}
                  <span className="font-semibold text-emerald-400 [html[data-theme=light]_&]:text-emerald-700">
                    {game.you_won}
                  </span>{" "}
                  –{" "}
                  <span className="font-semibold text-red-300 [html[data-theme=light]_&]:text-red-700">
                    {game.they_won}
                  </span>{" "}
                  {friendName}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

/**
 * The signed-in user's record against a friend, from the games both played
 * in, for the friend's profile page.
 */
export default function HeadToHeadSection({
  userId,
  friendName,
}: {
  userId: string;
  friendName: string;
}) {
  const result = useHeadToHead(userId);

  return (
    <section className="mt-8 rounded-2xl border border-border bg-surface p-6">
      <div className="mb-4 flex items-center gap-2">
        <Gamepad2 className="h-6 w-6 text-link" />

        <h2 className="text-xl font-bold text-foreground">Head to Head</h2>
      </div>

      <HeadToHeadBody result={result} friendName={friendName} />
    </section>
  );
}

/** The loading, error, empty or filled state of the head-to-head section. */
function HeadToHeadBody({
  result,
  friendName,
}: {
  result: HeadToHeadResult | null;
  friendName: string;
}) {
  if (result === null) {
    return (
      <p role="status" className="text-subtle">
        Loading your record...
      </p>
    );
  }

  if (result.error || result.record === null) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-red-500/40 bg-red-500/10 p-5 text-red-300 [html[data-theme=light]_&]:text-red-700"
      >
        {result.error}
      </div>
    );
  }

  if (result.record.sessions_together === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-background p-8 text-center">
        <p className="text-subtle">You haven&apos;t played together yet.</p>

        <p className="mt-2 text-sm text-muted">
          Log a game with {friendName} to start your record.
        </p>
      </div>
    );
  }

  return <HeadToHeadRecord record={result.record} friendName={friendName} />;
}
