"use client";

import { useEffect, useState } from "react";

type Game = {
  primary_name: string;
};

type PlaySession = {
  id: number;
  game: Game;
  play_date: string;
};

type LibraryItem = {
  game: Game;
  ownership: "OWNED" | "WISHLISTED";
  added_at: string;
};

type Activity = {
  id: string;
  message: string;
  gameName: string;
  date: string;
  type: "play" | "library" | "wishlist";
};

function isGame(value: unknown): value is Game {
  return (
    typeof value === "object" &&
    value !== null &&
    "primary_name" in value &&
    typeof value.primary_name === "string"
  );
}

function isPlaySession(value: unknown): value is PlaySession {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    typeof value.id === "number" &&
    "game" in value &&
    isGame(value.game) &&
    "play_date" in value &&
    typeof value.play_date === "string"
  );
}

function isLibraryItem(value: unknown): value is LibraryItem {
  return (
    typeof value === "object" &&
    value !== null &&
    "game" in value &&
    isGame(value.game) &&
    "ownership" in value &&
    (value.ownership === "OWNED" || value.ownership === "WISHLISTED") &&
    "added_at" in value &&
    typeof value.added_at === "string"
  );
}

function extractResults(data: unknown): unknown[] {
  if (Array.isArray(data)) {
    return data;
  }

  if (
    typeof data === "object" &&
    data !== null &&
    "results" in data &&
    Array.isArray(data.results)
  ) {
    return data.results;
  }

  throw new Error("Unexpected activity response.");
}

async function fetchActivityData(
  url: string,
  signal: AbortSignal,
): Promise<unknown[]> {
  const response = await fetch(url, {
    method: "GET",
    credentials: "same-origin",
    cache: "no-store",
    signal,
  });

  if (response.status === 401 || response.status === 403) {
    throw new Error("Please log in to view your activity.");
  }

  if (!response.ok) {
    throw new Error("Unable to load recent activity.");
  }

  const data: unknown = await response.json();

  return extractResults(data);
}

function createPlayActivities(data: unknown[]): Activity[] {
  return data.filter(isPlaySession).map((play) => ({
    id: `play-${play.id}`,
    message: "You played",
    gameName: play.game.primary_name,
    date: play.play_date,
    type: "play",
  }));
}

function createLibraryActivities(data: unknown[]): Activity[] {
  return data.filter(isLibraryItem).map((item, index) => ({
    id: `library-${index}`,
    message:
      item.ownership === "WISHLISTED"
        ? "You added to your wishlist"
        : "You added to your library",
    gameName: item.game.primary_name,
    date: item.added_at,
    type: item.ownership === "WISHLISTED" ? "wishlist" : "library",
  }));
}

function formatDate(date: string): string {
  const parsed = new Date(date);

  if (Number.isNaN(parsed.getTime())) {
    return date;
  }

  return parsed.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

function combineActivities(plays: unknown[], library: unknown[]): Activity[] {
  return [...createPlayActivities(plays), ...createLibraryActivities(library)]
    .filter((activity) => Number.isFinite(Date.parse(activity.date)))
    .sort((a, b) => Date.parse(b.date) - Date.parse(a.date))
    .slice(0, 8);
}

export default function UpdatesFeed() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadActivity() {
      try {
        const [plays, library] = await Promise.all([
          fetchActivityData("/api/v1/plays/", controller.signal),
          fetchActivityData("/api/v1/library/", controller.signal),
        ]);

        const recentActivities = combineActivities(plays, library);

        if (!controller.signal.aborted) {
          setActivities(recentActivities);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load recent activity.",
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadActivity();

    return () => controller.abort();
  }, []);

  return (
    <section>
      <h2 className="mb-2 text-3xl font-bold tracking-wide">RECENT UPDATES</h2>

      <p className="mb-6 text-sm text-gray-400">
        Your recent QuestLog activity
      </p>

      {loading && <p className="text-gray-400">Loading recent activity...</p>}

      {!loading && error && (
        <p role="alert" className="text-red-400">
          {error}
        </p>
      )}

      {!loading && !error && activities.length === 0 && (
        <div className="rounded-xl border border-gray-700 bg-slate-800/40 p-6">
          <p className="text-lg font-semibold">No recent activity yet</p>

          <p className="mt-2 text-sm text-gray-400">
            Start logging play sessions or adding games to your library to see
            updates here.
          </p>
        </div>
      )}

      {!loading && !error && activities.length > 0 && (
        <ul className="space-y-5">
          {activities.map((activity) => (
            <li key={activity.id} className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-gray-600 bg-indigo-500/20 text-xl">
                {activity.type === "play"
                  ? "🎲"
                  : activity.type === "wishlist"
                    ? "💌"
                    : "📚"}
              </div>

              <div className="min-w-0">
                <p className="text-lg leading-relaxed">
                  {activity.message}{" "}
                  <span className="font-semibold text-indigo-300">
                    {activity.gameName}
                  </span>
                </p>

                <p className="mt-1 text-sm text-gray-400">
                  {formatDate(activity.date)}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
