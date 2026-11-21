"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
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
  ImagePlus,
  Trash2,
  Camera,
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

const COVER_ENDPOINT = "/api/v1/profile/cover/";
const MAX_COVER_BYTES = 5 * 1024 * 1024;

function getCsrfToken(): string {
  const cookie = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith("csrf_token="));
  return cookie ? decodeURIComponent(cookie.slice("csrf_token=".length)) : "";
}

async function fetchCover(signal?: AbortSignal): Promise<string | null> {
  const response = await fetch(COVER_ENDPOINT, {
    credentials: "include",
    cache: "no-store",
    signal,
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("Unable to load your saved cover image.");
  return URL.createObjectURL(await response.blob());
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
  coverUrl,
  onUpload,
  onRemove,
  coverBusy,
  coverMessage,
}: {
  profile: UserProfile;
  appearance: LocalProfile;
  coverUrl: string | null;
  onUpload: (file: File) => void;
  onRemove: () => void;
  coverBusy: boolean;
  coverMessage: string;
}) {
  const displayName = profile.display_name || "QuestLog Player";
  const initial = displayName.charAt(0).toUpperCase();
  const coverInputRef = useRef<HTMLInputElement>(null);
  const shownCover = coverUrl || appearance.cover;

  return (
    <div className="relative isolate overflow-hidden rounded-2xl border border-border bg-indigo-950 text-white shadow-xl">
      {/* COVER */}
      <div className="absolute inset-0 -z-20 overflow-hidden">
        {shownCover ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={shownCover}
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
      {/* Compact cover actions: open only when the camera icon is clicked. */}
      <div className="absolute right-4 top-4 z-10">
        <input
          ref={coverInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          aria-label="Choose a profile cover image"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onUpload(file);
            event.target.value = "";
          }}
        />
        <details className="group relative">
          <summary
            aria-label="Cover image options"
            className="flex h-9 w-9 cursor-pointer list-none items-center justify-center rounded-full bg-black/65 text-white shadow-md transition hover:bg-black/85 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white [&::-webkit-details-marker]:hidden"
          >
            <Camera className="h-4 w-4" aria-hidden="true" />
          </summary>
          <div className="absolute right-0 top-11 w-44 overflow-hidden rounded-xl border border-white/20 bg-slate-900 p-1 shadow-xl">
            <button
              type="button"
              disabled={coverBusy}
              onClick={(event) => {
                event.currentTarget.closest("details")?.removeAttribute("open");
                coverInputRef.current?.click();
              }}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-white hover:bg-white/10 disabled:opacity-50"
            >
              <ImagePlus className="h-4 w-4" /> Change cover
            </button>
            {shownCover && (
              <button
                type="button"
                disabled={coverBusy}
                onClick={(event) => {
                  event.currentTarget.closest("details")?.removeAttribute("open");
                  onRemove();
                }}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-white hover:bg-white/10 disabled:opacity-50"
              >
                <Trash2 className="h-4 w-4" /> Remove cover
              </button>
            )}
          </div>
        </details>
      </div>
      {coverMessage && (
        <p role="status" className="absolute bottom-2 right-4 z-10 max-w-xs rounded-lg bg-black/75 px-3 py-2 text-xs text-white">
          {coverMessage}
        </p>
      )}
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
  const [coverUrl, setCoverUrl] = useState<string | null>(null);
  const [coverBusy, setCoverBusy] = useState(false);
  const [coverMessage, setCoverMessage] = useState("");

  useEffect(() => {
    return () => {
      if (coverUrl) URL.revokeObjectURL(coverUrl);
    };
  }, [coverUrl]);

  async function uploadCover(file: File) {
    if (!(["image/jpeg", "image/png", "image/webp"].includes(file.type))) {
      setCoverMessage("Choose a JPG, PNG, or WebP image.");
      return;
    }
    if (file.size > MAX_COVER_BYTES) {
      setCoverMessage("Cover images must be 5 MB or smaller.");
      return;
    }
    setCoverBusy(true);
    setCoverMessage("");
    try {
      const form = new FormData();
      form.append("cover_image", file);
      const response = await fetch(COVER_ENDPOINT, {
        method: "POST",
        credentials: "include",
        headers: { "X-CSRFToken": getCsrfToken() },
        body: form,
      });
      if (!response.ok) throw new Error(`Upload failed (${response.status}).`);
      const url = await fetchCover();
      setCoverUrl(url);
      setAppearance((previous) => ({ ...previous, cover: "" }));
      setCoverMessage("Cover image saved!");
    } catch (caught) {
      setCoverMessage(getErrorMessage(caught));
    } finally {
      setCoverBusy(false);
    }
  }

  async function removeCover() {
    setCoverBusy(true);
    setCoverMessage("");
    try {
      const response = await fetch(COVER_ENDPOINT, {
        method: "DELETE",
        credentials: "include",
        headers: { "X-CSRFToken": getCsrfToken() },
      });
      if (!response.ok) throw new Error(`Unable to remove cover (${response.status}).`);
      setCoverUrl(null);
      setAppearance((previous) => ({ ...previous, cover: "" }));
      // Remove old local-only cover so it doesn't reappear after refresh.
      localStorage.removeItem("userCover");
      const saved = localStorage.getItem("userProfile");
      if (saved) {
        try {
          const parsed: unknown = JSON.parse(saved);
          if (isRecord(parsed)) {
            delete parsed.cover;
            localStorage.setItem("userProfile", JSON.stringify(parsed));
          }
        } catch {
          // Ignore invalid legacy local profile data.
        }
      }
      setCoverMessage("Cover image removed.");
    } catch (caught) {
      setCoverMessage(getErrorMessage(caught));
    } finally {
      setCoverBusy(false);
    }
  }

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
        try {
          const savedCover = await fetchCover(controller.signal);
          if (controller.signal.aborted) {
            if (savedCover) URL.revokeObjectURL(savedCover);
            return;
          }
          setCoverUrl(savedCover);
        } catch (coverError) {
          if (!controller.signal.aborted) setCoverMessage(getErrorMessage(coverError));
        }
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

        <ProfileHeader
          profile={profile}
          appearance={appearance}
          coverUrl={coverUrl}
          onUpload={(file) => void uploadCover(file)}
          onRemove={() => void removeCover()}
          coverBusy={coverBusy}
          coverMessage={coverMessage}
        />

        <PlayerStats />

        <RecentActivity />
      </motion.div>
    </main>
  );
}

