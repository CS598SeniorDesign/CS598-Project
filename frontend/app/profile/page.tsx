"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  BookOpen,
  CalendarDays,
  Gamepad2,
  Settings,
  Trophy,
  Users,
  Pencil,
  Clock3,
  ArrowRight,
} from "lucide-react";

type UserProfile = {
  user_id: string;
  avatar: string;
  display_name: string;
  bio: string;
  privacy_level: "PUBLIC" | "FRIENDS" | "PRIVATE";
  bgg_username: string;
};

type LocalProfile = {
  avatar?: string;
  cover?: string;
};

function getSavedAppearance(): LocalProfile {
  if (typeof window === "undefined") return {};

  let appearance: LocalProfile = {};

  try {
    const saved = localStorage.getItem("userProfile");

    if (saved) {
      appearance = JSON.parse(saved) as LocalProfile;
    }
  } catch {
    console.error("Unable to read saved profile appearance.");
  }

  try {
    return {
      avatar: localStorage.getItem("userAvatar") || appearance.avatar || "",
      cover: localStorage.getItem("userCover") || appearance.cover || "",
    };
  } catch {
    return appearance;
  }
}

async function fetchOwnProfile(signal: AbortSignal): Promise<UserProfile> {
  const response = await fetch("/api/v1/profile/", {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error(
      response.status === 401 || response.status === 403
        ? "Please log in to view your profile."
        : "Unable to load your profile.",
    );
  }

  return (await response.json()) as UserProfile;
}

type ApiGame = {
  bgg_id: number;
  primary_name: string;
  thumbnail_url: string | null;
  average_rating: number | null;
};

type ApiPlayer = {
  id: number;
  user: string | null;
  guest_name: string;
  score: number | null;
  is_winner: boolean;
};

type ApiPlay = {
  id: number;
  game: ApiGame;
  play_date: string;
  play_time_minutes: number | null;
  quantity: number;
  players: ApiPlayer[];
};

type Friend = {
  user_id: string;
  display_name: string;
};

type Loadable<T> = {
  data: T;
  loading: boolean;
  error: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isGame(value: unknown): value is ApiGame {
  if (!isRecord(value)) return false;

  return (
    typeof value.bgg_id === "number" && typeof value.primary_name === "string"
  );
}

function isPlay(value: unknown): value is ApiPlay {
  if (!isRecord(value)) return false;

  return (
    typeof value.id === "number" &&
    typeof value.play_date === "string" &&
    isGame(value.game) &&
    Array.isArray(value.players)
  );
}

function isFriend(value: unknown): value is Friend {
  if (!isRecord(value)) return false;

  return (
    typeof value.user_id === "string" && typeof value.display_name === "string"
  );
}

function extractResults(data: unknown): unknown[] {
  if (Array.isArray(data)) return data;

  if (isRecord(data) && Array.isArray(data.results)) {
    return data.results;
  }

  throw new Error("Unexpected API response.");
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unable to load data.";
}

function useApiList<T>(
  url: string,
  validator: (value: unknown) => value is T,
): Loadable<T[]> {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const response = await fetch(url, {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Request failed (${response.status}).`);
        }

        const payload: unknown = await response.json();
        const results = extractResults(payload);

        if (!controller.signal.aborted) {
          setData(results.filter(validator));
        }
      } catch (caught) {
        if (!controller.signal.aborted) {
          setError(getErrorMessage(caught));
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => controller.abort();
  }, [url, validator]);

  return { data, loading, error };
}

type ProfileSummary = {
  games_owned: number;
  total_sessions: number;
  wins: number;
};

function useProfileSummary() {
  const [data, setData] = useState<ProfileSummary | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch("/api/v1/analytics/summary/", {
          credentials: "same-origin",
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Unable to load player statistics.");
        const summary = (await response.json()) as ProfileSummary;
        if (!controller.signal.aborted) setData(summary);
      } catch (err) {
        if (!controller.signal.aborted) setError(getErrorMessage(err));
      }
    }
    void load();
    return () => controller.abort();
  }, []);
  return { data, error };
}

function ProfileStatCard({
  title,
  icon: Icon,
  description,
  href,
  value,
}: {
  title: string;
  icon: typeof Gamepad2;
  description: string;
  href: string;
  value: number | undefined;
}) {
  return (
    <Link
      href={href}
      className="group block rounded-2xl border border-border bg-surface p-5 transition hover:border-indigo-500 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500"
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="rounded-xl bg-indigo-500/10 p-3">
          <Icon className="h-6 w-6 text-link" />
        </div>
        <ArrowRight className="h-5 w-5 text-link transition group-hover:translate-x-1" />
      </div>

      <p className="text-3xl font-bold text-foreground">{value ?? "—"}</p>

      <h3 className="mt-2 font-semibold text-subtle">{title}</h3>

      <p className="mt-1 text-xs text-muted">{description}</p>
    </Link>
  );
}

function PlayerStats() {
  const summary = useProfileSummary();
  const friends = useApiList("/api/v1/friends/", isFriend);
  return (
    <section className="mt-8">
      <div className="mb-5 flex items-center gap-2">
        <Gamepad2 className="h-6 w-6 text-link" />
        <h2 className="text-2xl font-bold">Player Stats</h2>
      </div>

      {summary.error && (
        <p role="alert" className="mb-3 text-sm text-muted">
          {summary.error}
        </p>
      )}
      {friends.error && (
        <p role="alert" className="mb-3 text-sm text-muted">
          Unable to load friend count.
        </p>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <ProfileStatCard
          title="Owned Games"
          href="/library"
          value={summary.data?.games_owned}
          icon={BookOpen}
          description="Games you own in your library"
        />

        <ProfileStatCard
          title="Sessions Played"
          href="/analytics#player-stats"
          value={summary.data?.total_sessions}
          icon={CalendarDays}
          description="Logged game sessions"
        />

        <ProfileStatCard
          title="Games Won"
          href="/analytics#win-rate"
          value={summary.data?.wins}
          icon={Trophy}
          description="Your victories"
        />

        <ProfileStatCard
          title="Friends"
          href="/community#friends"
          value={
            friends.loading || friends.error ? undefined : friends.data.length
          }
          icon={Users}
          description="Your QuestLog connections"
        />
      </div>
    </section>
  );
}

function formatPlayDate(date: string): string {
  const [year, month, day] = date.split("-").map(Number);
  const parsed = new Date(year, month - 1, day);

  if (Number.isNaN(parsed.getTime())) return date;

  return parsed.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function RecentActivity() {
  const plays = useApiList("/api/v1/plays/", isPlay);
  const recent = [...plays.data]
    .sort((a, b) => b.play_date.localeCompare(a.play_date) || b.id - a.id)
    .slice(0, 4);
  return (
    <section className="mt-8 rounded-2xl border border-border bg-surface p-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-xl font-bold">
          <Clock3 className="h-6 w-6 text-link" /> Recent Activity
        </h2>
        <Link
          href="/dashboardPpt#recent-plays"
          className="inline-flex items-center gap-2 text-sm font-semibold text-link hover:underline"
        >
          View Recent Plays <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
      {plays.loading ? (
        <p role="status" className="text-muted">
          Loading recent activity...
        </p>
      ) : plays.error ? (
        <p role="alert" className="text-muted">
          {plays.error}
        </p>
      ) : recent.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border p-8 text-center text-muted">
          No plays logged yet. Visit your dashboard to get started.
        </p>
      ) : (
        <div className="space-y-3">
          {recent.map((play) => (
            <Link
              key={play.id}
              href={`/games/${play.game.bgg_id}`}
              className="flex items-center gap-4 rounded-xl border border-border bg-background p-4 transition hover:bg-surface-hover"
            >
              <Gamepad2 className="h-6 w-6 shrink-0 text-link" />
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{play.game.primary_name}</p>
                <p className="text-sm text-muted">
                  {formatPlayDate(play.play_date)} · {play.players.length}{" "}
                  players
                </p>
              </div>
              <ArrowRight className="h-5 w-5 shrink-0 text-link" />
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}

function ProfileHeader({
  profile,
  appearance,
}: {
  profile: UserProfile;
  appearance: LocalProfile;
}) {
  const displayName = profile.display_name || "QuestLog Player";
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <div className="relative isolate overflow-hidden rounded-2xl border border-border bg-indigo-950 text-white shadow-xl">
      {/* COVER */}
      <div className="absolute inset-0 -z-20 overflow-hidden">
        {appearance.cover ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={appearance.cover}
            alt=""
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="h-full w-full bg-gradient-to-r from-indigo-900 via-indigo-700 to-emerald-700" />
        )}
      </div>

      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-gradient-to-t from-black/90 via-black/60 to-black/10"
      />
      {/* PROFILE DETAILS */}
      <div className="relative px-6 pb-8 pt-32 sm:px-10 sm:pt-40">
        <div className="mb-4 flex items-end justify-between">
          <div className="relative flex h-28 w-28 items-center justify-center overflow-hidden rounded-full border-4 border-white bg-indigo-600 text-white text-4xl font-bold shadow-lg sm:h-32 sm:w-32">
            {appearance.avatar ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={appearance.avatar}
                alt={`${displayName}'s avatar`}
                className="h-full w-full object-cover"
              />
            ) : (
              <span>{initial}</span>
            )}
          </div>
        </div>

        <h2 className="text-2xl font-bold">{displayName}</h2>

        <p className="mt-2 max-w-2xl whitespace-pre-wrap break-words text-slate-100">
          {profile.bio || "Add a bio to introduce yourself to other players!"}
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <span className="rounded-full border border-white/50 bg-black/40 px-4 py-2 text-sm capitalize text-white">
            Privacy: {profile.privacy_level.toLowerCase()}
          </span>

          {profile.bgg_username && (
            <span className="rounded-full border border-emerald-300/60 bg-black/40 px-4 py-2 text-sm text-emerald-100">
              BGG: {profile.bgg_username}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [appearance, setAppearance] = useState<LocalProfile>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadProfile() {
      try {
        const data = await fetchOwnProfile(controller.signal);
        const savedAppearance = getSavedAppearance();

        if (controller.signal.aborted) return;

        setProfile(data);
        setAppearance({
          ...savedAppearance,
          avatar: data.avatar || savedAppearance.avatar,
        });
      } catch (err) {
        if (controller.signal.aborted) return;

        setError(err instanceof Error ? err.message : "Something went wrong.");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadProfile();

    return () => controller.abort();
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen bg-background p-8 text-foreground">
        <p className="text-subtle">Loading your profile...</p>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="min-h-screen bg-background p-8 text-foreground">
        <h1 className="mb-4 text-3xl font-bold">Your Profile</h1>

        <p
          role="alert"
          className="mb-6 text-red-400 [html[data-theme=light]_&]:text-red-700"
        >
          {error || "Your profile is unavailable."}
        </p>

        <Link
          href="/login"
          className="inline-block rounded-xl bg-indigo-600 text-white px-5 py-2 hover:bg-indigo-500"
        >
          Go to Login
        </Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background px-4 py-8 text-foreground sm:px-8">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="mx-auto max-w-5xl"
      >
        {/* PAGE TITLE */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Your Profile</h1>

            <p className="mt-1 text-sm text-muted">
              Your personal space in the QuestLog community.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              href="/profile/edit"
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 text-white px-5 py-2.5 text-sm font-semibold transition hover:bg-indigo-500"
            >
              <Pencil className="h-4 w-4" />
              Edit Profile
            </Link>

            <Link
              href="/settings"
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface px-5 py-2.5 text-sm font-semibold transition hover:bg-surface-hover"
            >
              <Settings className="h-4 w-4" />
              Settings
            </Link>
          </div>
        </div>

        <ProfileHeader profile={profile} appearance={appearance} />

        <PlayerStats />

        <RecentActivity />
      </motion.div>
    </main>
  );
}
