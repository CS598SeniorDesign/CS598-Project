"use client";

import { useEffect, useState } from "react";
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  Clock3,
  Gamepad2,
  Heart,
  Users,
} from "lucide-react";

type Game = {
  bgg_id: number;
  primary_name: string;
};

type FeedActor = {
  user_id: string;
  display_name: string;
  is_you: boolean;
};

type ActivityType = "play" | "library" | "wishlist";
type Filter = "all" | "play" | "collection";

type Activity = {
  id: string;
  type: ActivityType;
  actor: FeedActor | null;
  game: Game | null;
  occurred_at: string;
};

type FeedState = {
  activities: Activity[];
  loading: boolean;
  error: string;
};

const INITIAL_VISIBLE = 5;

const FILTERS: { label: string; value: Filter }[] = [
  { label: "All", value: "all" },
  { label: "Plays", value: "play" },
  { label: "Collections", value: "collection" },
];

const ACTIVITY_STYLES = {
  play: {
    Icon: Gamepad2,
    color: "text-emerald-300 bg-emerald-500/15",
    label: "Play session",
  },
  library: {
    Icon: BookOpen,
    color: "text-indigo-300 bg-indigo-500/15",
    label: "Library",
  },
  wishlist: {
    Icon: Heart,
    color: "text-pink-300 bg-pink-500/15",
    label: "Wishlist",
  },
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isGame(value: unknown): value is Game {
  if (!isRecord(value)) return false;

  return (
    typeof value.bgg_id === "number" && typeof value.primary_name === "string"
  );
}

function isActor(value: unknown): value is FeedActor {
  if (!isRecord(value)) return false;

  return (
    typeof value.user_id === "string" &&
    typeof value.display_name === "string" &&
    typeof value.is_you === "boolean"
  );
}

function isActivityType(value: unknown): value is ActivityType {
  return value === "play" || value === "library" || value === "wishlist";
}

function isActivity(value: unknown): value is Activity {
  if (!isRecord(value)) return false;

  const validActor = value.actor == null || isActor(value.actor);
  const validGame = value.game == null || isGame(value.game);

  const validFields = [
    typeof value.id === "string",
    isActivityType(value.type),
    typeof value.occurred_at === "string",
    validActor,
    validGame,
  ];

  return validFields.every(Boolean);
}

function getRelativeDate(value: string): string {
  const date = new Date(value);
  const difference = Date.now() - date.getTime();

  if (!Number.isFinite(difference)) return "Unknown date";

  if (difference < 0) {
    return formatShortDate(date);
  }

  const minutes = Math.floor(difference / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d ago`;

  return formatShortDate(date);
}

function formatShortDate(date: Date): string {
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function getInitials(name: string): string {
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");

  return initials || "?";
}

function getActorName(activity: Activity): string {
  if (activity.actor?.is_you) return "You";

  return activity.actor?.display_name ?? "A player";
}

function getActivityText(activity: Activity) {
  const name = getActorName(activity);
  const possessive = activity.actor?.is_you ? "your" : "their";

  if (activity.type === "play") {
    return {
      name,
      action: "played",
      suffix: "",
    };
  }

  if (activity.type === "wishlist") {
    return {
      name,
      action: "added",
      suffix: `to ${possessive} wishlist`,
    };
  }

  return {
    name,
    action: "added",
    suffix: `to ${possessive} library`,
  };
}

function matchesFilter(activity: Activity, filter: Filter): boolean {
  if (filter === "all") return true;

  if (filter === "play") {
    return activity.type === "play";
  }

  return activity.type !== "play";
}

async function fetchCommunityFeed(signal: AbortSignal): Promise<Activity[]> {
  const response = await fetch("/api/v1/community/feed/?limit=20", {
    method: "GET",
    credentials: "same-origin",
    cache: "no-store",
    signal,
  });

  if (response.status === 401 || response.status === 403) {
    throw new Error("Please log in to view community activity.");
  }

  if (!response.ok) {
    throw new Error("Unable to load community updates.");
  }

  const data: unknown = await response.json();

  if (!Array.isArray(data)) {
    throw new Error("Unexpected community feed response.");
  }

  return data
    .filter(isActivity)
    .map((activity) => ({
      ...activity,
      actor: activity.actor ?? null,
      game: activity.game ?? null,
    }))
    .sort((a, b) => Date.parse(b.occurred_at) - Date.parse(a.occurred_at));
}

function useCommunityFeed(): FeedState {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadFeed() {
      try {
        const result = await fetchCommunityFeed(controller.signal);

        if (controller.signal.aborted) return;

        setActivities(result);
        setError("");
      } catch (err) {
        if (controller.signal.aborted) return;

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load community updates.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadFeed();

    return () => controller.abort();
  }, []);

  return { activities, loading, error };
}

function FeedHeader({ count }: { count: number | null }) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold tracking-wide sm:text-3xl">
            RECENT UPDATES
          </h2>

          {count !== null && (
            <span className="rounded-full border border-indigo-400/20 bg-indigo-500/15 px-2.5 py-1 text-xs font-semibold text-indigo-300">
              {count}
            </span>
          )}
        </div>

        <p className="mt-2 text-sm text-slate-400">
          See what&apos;s happening in your circle.
        </p>
      </div>

      <div className="rounded-lg bg-indigo-500/10 p-2.5 text-indigo-300">
        <Users className="h-5 w-5" />
      </div>
    </div>
  );
}

function FeedFilters({
  selected,
  onChange,
}: {
  selected: Filter;
  onChange: (value: Filter) => void;
}) {
  return (
    <div className="mb-5 flex flex-wrap gap-2">
      {FILTERS.map((option) => {
        const active = selected === option.value;

        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={`rounded-full border px-4 py-2 text-xs font-semibold transition-colors ${
              active
                ? "border-indigo-500 bg-indigo-600 text-white"
                : "border-slate-700 bg-slate-800/60 text-slate-300 hover:border-indigo-400/50 hover:text-white"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

function FeedLoading() {
  return (
    <div role="status" className="space-y-3">
      {[1, 2, 3].map((item) => (
        <div
          key={item}
          className="h-20 animate-pulse rounded-xl border border-slate-700/60 bg-slate-800/50"
        />
      ))}

      <span className="sr-only">Loading community updates...</span>
    </div>
  );
}

function FeedEmpty({ hasActivity }: { hasActivity: boolean }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/40 px-5 py-9 text-center">
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-500/15">
        <Gamepad2 className="h-6 w-6 text-indigo-300" />
      </div>

      <h3 className="font-semibold">
        {hasActivity
          ? "No updates in this category"
          : "No community activity yet"}
      </h3>

      <p className="mx-auto mt-2 max-w-sm text-sm text-slate-400">
        {hasActivity
          ? "Try another filter to explore recent activity."
          : "Log a game, grow your collection, or connect with friends to get things started."}
      </p>
    </div>
  );
}

function ActivityCard({ activity }: { activity: Activity }) {
  const message = getActivityText(activity);
  const actorName = getActorName(activity);
  const style = ACTIVITY_STYLES[activity.type];
  const Icon = style.Icon;
  const date = new Date(activity.occurred_at);

  const dateTitle = Number.isNaN(date.getTime())
    ? undefined
    : date.toLocaleString();

  return (
    <article className="group rounded-xl border border-slate-700/70 bg-slate-800/45 p-4 transition-colors hover:border-indigo-500/40 hover:bg-slate-800/75">
      <div className="flex items-start gap-3">
        <div className="relative shrink-0">
          <div className="flex h-11 w-11 items-center justify-center rounded-full border border-indigo-400/25 bg-indigo-500/20 text-sm font-bold text-indigo-200">
            {getInitials(actorName)}
          </div>

          <div
            className={`absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full border-2 border-slate-800 ${style.color}`}
          >
            <Icon className="h-3 w-3" />
          </div>
        </div>

        <div className="min-w-0 flex-1">
          <p className="break-words text-sm leading-relaxed text-slate-200">
            <span className="font-bold text-white">{message.name}</span>{" "}
            {message.action}{" "}
            <span className="font-semibold text-indigo-300">
              {activity.game?.primary_name ?? "a game"}
            </span>
            {message.suffix ? ` ${message.suffix}` : ""}
          </p>

          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="inline-flex items-center gap-1 text-xs text-slate-400">
              <Clock3 className="h-3 w-3" />

              <time
                dateTime={activity.occurred_at}
                title={dateTitle}
                suppressHydrationWarning
              >
                {getRelativeDate(activity.occurred_at)}
              </time>
            </span>

            <span className="text-xs text-slate-500">{style.label}</span>
          </div>
        </div>
      </div>
    </article>
  );
}

function FeedActivityList({ activities }: { activities: Activity[] }) {
  return (
    <div className="space-y-3">
      {activities.map((activity) => (
        <ActivityCard key={activity.id} activity={activity} />
      ))}
    </div>
  );
}

function ShowMoreButton({
  expanded,
  remaining,
  onClick,
}: {
  expanded: boolean;
  remaining: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800/40 px-4 py-3 text-sm font-semibold text-indigo-300 transition-colors hover:border-indigo-500/40 hover:bg-slate-800"
    >
      {expanded ? (
        <>
          Show Less
          <ChevronUp className="h-4 w-4" />
        </>
      ) : (
        <>
          Show More ({remaining} more)
          <ChevronDown className="h-4 w-4" />
        </>
      )}
    </button>
  );
}

function FeedContent({
  activities,
  loading,
  error,
  filter,
  expanded,
  onToggleExpanded,
}: FeedState & {
  filter: Filter;
  expanded: boolean;
  onToggleExpanded: () => void;
}) {
  if (loading) return <FeedLoading />;

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-red-500/30 bg-red-500/10 p-5 text-sm text-red-300"
      >
        {error}
      </div>
    );
  }

  const filtered = activities.filter((activity) =>
    matchesFilter(activity, filter),
  );

  if (filtered.length === 0) {
    return <FeedEmpty hasActivity={activities.length > 0} />;
  }

  const visible = expanded ? filtered : filtered.slice(0, INITIAL_VISIBLE);

  const hasMore = filtered.length > INITIAL_VISIBLE;

  return (
    <>
      <FeedActivityList activities={visible} />

      {hasMore && (
        <ShowMoreButton
          expanded={expanded}
          remaining={filtered.length - INITIAL_VISIBLE}
          onClick={onToggleExpanded}
        />
      )}
    </>
  );
}

export default function UpdatesFeed() {
  const feed = useCommunityFeed();
  const [filter, setFilter] = useState<Filter>("all");
  const [expanded, setExpanded] = useState(false);

  function handleFilterChange(value: Filter) {
    setFilter(value);
    setExpanded(false);
  }

  function toggleExpanded() {
    setExpanded((previous) => !previous);
  }

  const count = feed.loading || feed.error ? null : feed.activities.length;

  return (
    <section className="min-w-0 text-slate-100">
      <FeedHeader count={count} />

      <FeedFilters selected={filter} onChange={handleFilterChange} />

      <FeedContent
        {...feed}
        filter={filter}
        expanded={expanded}
        onToggleExpanded={toggleExpanded}
      />
    </section>
  );
}
