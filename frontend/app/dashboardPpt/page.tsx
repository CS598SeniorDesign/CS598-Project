"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Link from "next/link";
import RecommendationStrip from "@/components/recommendations/RecommendationStrip";
// import WinRateChart from "@/components/stats/WinRateChart";

// avatars
import brandonAvatar from "@/public/avatars/brandon.webp";
import sydneyAvatar from "@/public/avatars/sydney.webp";
import jenniferAvatar from "@/public/avatars/jennifer.webp";
import supriyaAvatar from "@/public/avatars/supriya.webp";
import { StaticImageData } from "next/image";

// game images
import terraformImg from "@/public/images/terraforming.webp";
import catanImg from "@/public/images/catan.webp";
import everdellImg from "@/public/images/everdell.webp";
import botanyImg from "@/public/images/botany.webp";

type BaseGame = {
  gameName: string;
  gameImg: string | StaticImageData;
};

type GameResult = BaseGame & {
  gameResult: "Won" | "Lost";
  //TODO: extend to include score or draw in future
};

type Game = BaseGame;

type Play = GameResult & {
  playerCount: number;
  playDuration: string;
  playDate: string;
};

type CommunityItem = GameResult & {
  user: string;
  timeAgo: string;
  avatar?: string | StaticImageData;
};

const days: string[] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const subscribeToUserAvatar = () => {
  return () => {};
};

const getUserAvatarSnapshot = () => {
  return localStorage.getItem("userAvatar");
};

const getUserAvatarServerSnapshot = () => {
  return null;
};

export default function Page() {
  // const [openChart, setOpenChart] = useState<null | "winrate" | "donut">(null);

import { useEffect, useMemo, useState } from "react";

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

type FeedActivity = {
  id: string;
  type: "play" | "library" | "wishlist";
  actor: {
    user_id: string;
    display_name: string;
    is_you: boolean;
  } | null;
  game: ApiGame;
  occurred_at: string;
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

const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const cardClass =
  "rounded-2xl bg-[#1E293B]/70 p-5 shadow-lg transition duration-300 hover:shadow-xl hover:shadow-indigo-500/10";

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

function isFeedActor(value: unknown): boolean {
  if (value === null) return true;
  if (!isRecord(value)) return false;

  return (
    typeof value.user_id === "string" && typeof value.display_name === "string"
  );
}

function isFeedActivity(value: unknown): value is FeedActivity {
  if (!isRecord(value)) return false;

  return (
    typeof value.id === "string" &&
    ["play", "library", "wishlist"].includes(String(value.type)) &&
    typeof value.occurred_at === "string" &&
    isGame(value.game) &&
    isFeedActor(value.actor)
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

function useProfileName(): Loadable<string> {
  const [data, setData] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const response = await fetch("/api/v1/profile/", {
          credentials: "same-origin",
          cache: "no-store",
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error("Unable to load profile.");
        }

        const payload: unknown = await response.json();

        if (
          isRecord(payload) &&
          typeof payload.display_name === "string" &&
          !controller.signal.aborted
        ) {
          setData(payload.display_name);
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
  }, []);

  return { data, loading, error };
}

function useAvatar(): string | null {
  const [avatar, setAvatar] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("userAvatar");
    if (stored) {
      // Synchronize browser-only avatar after hydration.
      queueMicrotask(() => setAvatar(stored));
    }
  }, []);

  return avatar;
}

function getCsrfToken(): string | null {
  const entry = document.cookie
    .split("; ")
    .find((item) => item.startsWith("csrf_token="));

  return entry ? decodeURIComponent(entry.slice("csrf_token=".length)) : null;
}

function UserMenu() {
  const router = useRouter();
  const profile = useProfileName();
  const avatar = useAvatar();

  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");

  async function handleLogout() {
    if (loggingOut) return;

    setLoggingOut(true);
    setLogoutError("");

    try {
      const csrfToken = getCsrfToken();

      if (!csrfToken) {
        throw new Error("Missing CSRF token. Refresh and try again.");
      }

      const response = await fetch("/_allauth/browser/v1/auth/session", {
        method: "DELETE",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken,
        },
      });

      if (!response.ok && response.status !== 401) {
        throw new Error("Unable to log out.");
      }

      router.replace("/login");
      router.refresh();
    } catch (caught) {
      setLogoutError(getErrorMessage(caught));
      setLoggingOut(false);
    }
  }

  return (
    <div className=" min-h-screen bg-[#0F172A] text-[#F8FAFC]">
      {/* NAVBAR */}
      <div className="flex justify-between items-center px-8 py-4 bg-gradient-to-r from-[#1E293B] to-[#0F172A] shadow-xl">
        <h1 className="text-xl font-bold">QuestLog</h1>

        <div className="flex gap-10 text-gray-300">
          <p className="border-b-2 border-[#4F46E5] pb-1 cursor-pointer">
            Game Library
          </p>
          <Link href="/recommendations">
            <p className="hover:text-white cursor-pointer transition">
              Recommendations for you
            </p>
          </Link>
          <p className="hover:text-white cursor-pointer transition">Weeple</p>
          <Link href="/analytics">
            <p className="hover:text-white cursor-pointer transition">
              Your Analytics
            </p>
          </Link>
        </div>

        <div className="flex items-center gap-3">
          {userAvatar ? (
    <div className="flex flex-col items-end gap-2">
      <div className="flex items-center gap-3">
        <Link
          href="/profile"
          className="flex items-center gap-3 rounded-lg p-1 hover:bg-white/10"
        >
          {avatar ? (
            <Image
              src={avatar}
              alt="User avatar"
              width={32}
              height={32}
              className="h-8 w-8 rounded-full object-cover"
            />
          ) : (
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold">
              {profile.data.charAt(0).toUpperCase() || "?"}
            </div>
          )}

          <span className="max-w-36 truncate text-sm font-medium">
            {profile.loading ? "Loading..." : profile.data || "My Profile"}
          </span>
        </Link>

        <button
          type="button"
          onClick={() => void handleLogout()}
          disabled={loggingOut}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium transition hover:bg-indigo-500 disabled:opacity-50"
        >
          {loggingOut ? "Logging Out..." : "Log Out"}
        </button>
      </div>

      {logoutError && (
        <p role="alert" className="text-xs text-red-400">
          {logoutError}
        </p>
      )}
    </div>
  );
}

function DashboardNavbar() {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 bg-gradient-to-r from-[#1E293B] to-[#0F172A] px-4 py-4 shadow-xl sm:px-8">
      <Link href="/dashboardPpt" className="text-xl font-bold">
        QuestLog
      </Link>

      <nav
        aria-label="Dashboard navigation"
        className="flex flex-wrap items-center gap-4 text-gray-300 lg:gap-10"
      >
        <Link href="/library" className="hover:text-white">
          Game Library
        </Link>
        <Link href="/recommendations" className="hover:text-white">
          Recommendations for you
        </Link>
        <Link href="/community" className="hover:text-white">
          Weeple
        </Link>
        <Link href="/analytics" className="hover:text-white">
          Your Analytics
        </Link>
      </nav>

      <UserMenu />
    </header>
  );
}

function StatusMessage({
  loading,
  error,
  empty,
  hasData,
  loadingText,
  emptyText,
}: {
  loading: boolean;
  error: string;
  empty: boolean;
  hasData?: boolean;
  loadingText: string;
  emptyText: string;
}) {
  if (loading) {
    return <p className="text-sm text-gray-400">{loadingText}</p>;
  }

  if (error) {
    return (
      <p role="alert" className="text-sm text-red-400">
        {error}
      </p>
    );
  }

  if (empty && !hasData) {
    return <p className="text-sm text-gray-400">{emptyText}</p>;
  }

  return null;
}

function GameCover({
  game,
  width = 48,
  height = 48,
  className = "h-12 w-12 rounded-lg object-cover",
}: {
  game: ApiGame;
  width?: number;
  height?: number;
  className?: string;
}) {
  if (!game.thumbnail_url) {
    return (
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-slate-700 text-xl">
        🎲
      </div>
    );
  }

  return (
    <Image
      unoptimized
      src={game.thumbnail_url}
      alt={game.primary_name}
      width={width}
      height={height}
      className={className}
    />
  );
}

function uniqueRecentGames(plays: ApiPlay[]): ApiPlay[] {
  const seen = new Set<number>();

  return plays
    .filter((play) => {
      if (seen.has(play.game.bgg_id)) return false;

      seen.add(play.game.bgg_id);
      return true;
    })
    .slice(0, 8);
}

function RecentlyPlayed({ state }: { state: Loadable<ApiPlay[]> }) {
  const games = useMemo(() => uniqueRecentGames(state.data), [state.data]);

  return (
    <section className={`${cardClass} lg:col-span-2`}>
      <h2 className="mb-4 text-gray-300">Recently Played</h2>

      <StatusMessage
        loading={state.loading}
        error={state.error}
        empty={games.length === 0}
        loadingText="Loading recently played games..."
        emptyText="No plays logged yet. Log a play to see your games here."
      />

      <div className="flex gap-5 overflow-x-auto pb-2">
        {games.map(({ game }) => (
          <Link
            key={game.bgg_id}
            href={`/games/${game.bgg_id}`}
            className="block shrink-0"
          >
            <div className="w-36 sm:w-44">
              <GameCover
                game={game}
                width={200}
                height={160}
                className="mb-2 h-40 w-full rounded-xl object-cover transition duration-300 hover:scale-105 hover:shadow-[0_0_20px_rgba(79,70,229,0.4)]"
              />

              <p className="text-sm font-semibold">{game.primary_name}</p>

              {typeof game.average_rating === "number" && (
                <p className="text-sm text-[#FFBF00]">
                  BGG {game.average_rating.toFixed(1)}/10
                </p>
              )}
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

function makeCalendarCells(month: Date): (number | null)[] {
  const year = month.getFullYear();
  const monthIndex = month.getMonth();
  const offset = (new Date(year, monthIndex, 1).getDay() + 6) % 7;
  const count = new Date(year, monthIndex + 1, 0).getDate();

  return [
    ...Array.from({ length: offset }, () => null),
    ...Array.from({ length: count }, (_, index) => index + 1),
  ];
}

function makePlayCounts(plays: ApiPlay[]): Map<string, number> {
  const counts = new Map<string, number>();

  for (const play of plays) {
    counts.set(play.play_date, (counts.get(play.play_date) ?? 0) + 1);
  }

  return counts;
}

function dateKeyForDay(month: Date, day: number): string {
  const year = month.getFullYear();
  const monthNumber = String(month.getMonth() + 1).padStart(2, "0");
  const dayNumber = String(day).padStart(2, "0");

  return `${year}-${monthNumber}-${dayNumber}`;
}

function CalendarCell({
  day,
  month,
  counts,
}: {
  day: number | null;
  month: Date;
  counts: Map<string, number>;
}) {
  if (day === null) {
    return <div aria-hidden="true" className="h-12" />;
  }

  const count = counts.get(dateKeyForDay(month, day)) ?? 0;

  return (
    <div
      title={
        count > 0
          ? `${count} logged session${count === 1 ? "" : "s"}`
          : undefined
      }
      className="relative flex h-12 flex-col items-center justify-center rounded-lg bg-[#0F172A]"
    >
      {day}

      {count > 0 && (
        <span className="mt-0.5 rounded bg-[#10B981] px-1 text-[10px] text-[#0F172A]">
          {count} {count === 1 ? "play" : "plays"}
        </span>
      )}
    </div>
  );
}

function PlayCalendar({ plays }: { plays: ApiPlay[] }) {
  const [month, setMonth] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });

  const cells = useMemo(() => makeCalendarCells(month), [month]);
  const counts = useMemo(() => makePlayCounts(plays), [plays]);

  function changeMonth(offset: number) {
    setMonth(new Date(month.getFullYear(), month.getMonth() + offset, 1));
  }

  return (
    <section className={cardClass}>
      <h2 className="mb-2 text-gray-300">Calendar</h2>

      <div className="mb-3 flex items-center justify-between gap-2">
        <button
          type="button"
          aria-label="Previous month"
          onClick={() => changeMonth(-1)}
          className="rounded-lg px-3 py-1 hover:bg-[#4F46E5]"
        >
          ‹
        </button>

        <h3 className="text-center font-semibold tracking-wide">
          {month.toLocaleDateString("en-US", {
            month: "long",
            year: "numeric",
          })}
        </h3>

        <button
          type="button"
          aria-label="Next month"
          onClick={() => changeMonth(1)}
          className="rounded-lg px-3 py-1 hover:bg-[#4F46E5]"
        >
          ›
        </button>
      </div>

      <div className="mb-2 grid grid-cols-7 text-center text-xs text-gray-400">
        {weekdays.map((day) => (
          <div key={day}>{day}</div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1 text-center text-sm">
        {cells.map((day, index) => (
          <CalendarCell
            key={`${index}-${day ?? "empty"}`}
            day={day}
            month={month}
            counts={counts}
          />
        ))}
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

function RecentPlayItem({ play }: { play: ApiPlay }) {
  const winnerRecorded = play.players.some((player) => player.is_winner);

  return (
    <Link
      href={`/games/${play.game.bgg_id}`}
      className="mb-2 flex gap-3 rounded-lg bg-[#0F172A] p-3 transition hover:bg-[#28354E]"
    >
      <GameCover game={play.game} />

      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">{play.game.primary_name}</p>

        <p className="text-xs text-gray-400">
          {formatPlayDate(play.play_date)}
          {" | "}
          {play.players.length} players
          {play.play_time_minutes != null
            ? ` | ${play.play_time_minutes} min`
            : ""}
        </p>
      </div>

      {winnerRecorded && (
        <span className="text-xs font-semibold text-[#10B981]">
          Winner recorded
        </span>
      )}
    </Link>
  );
}

function RecentPlays({ state }: { state: Loadable<ApiPlay[]> }) {
  return (
    <section className={cardClass}>
      <h2 className="mb-3">Recent Plays</h2>

      <StatusMessage
        loading={state.loading}
        error={state.error}
        empty={state.data.length === 0}
        loadingText="Loading your play history..."
        emptyText="No play sessions yet."
      />

      {!state.loading &&
        !state.error &&
        state.data
          .slice(0, 5)
          .map((play) => <RecentPlayItem key={play.id} play={play} />)}
    </section>
  );
}

function formatActivityDate(date: string): string {
  const parsed = new Date(date);

  if (Number.isNaN(parsed.getTime())) return "";

  return parsed.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function activityVerb(item: FeedActivity): string {
  switch (item.type) {
    case "play":
      return "played";
    case "library":
      return item.actor?.is_you
        ? "added to your library"
        : "added to their library";
    case "wishlist":
      return item.actor?.is_you ? "added to your wishlist" : "wishlisted";
  }
}

function FeedActivityItem({ item }: { item: FeedActivity }) {
  const actorName = item.actor?.is_you
    ? "You"
    : item.actor?.display_name || "Player";

  return (
    <article className="mb-2 flex items-center gap-3 rounded-lg bg-[#0F172A] p-2">
      <div
        aria-hidden="true"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-600 font-semibold"
      >
        {actorName.charAt(0).toUpperCase()}
      </div>

      <Link
        href={`/games/${item.game.bgg_id}`}
        aria-label={`View ${item.game.primary_name}`}
      >
        <GameCover game={item.game} />
      </Link>

      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">
          {actorName}
          <span className="ml-2 text-xs font-normal text-gray-400">
            {formatActivityDate(item.occurred_at)}
          </span>
        </p>

        <p className="text-xs text-gray-400">
          {activityVerb(item)}{" "}
          <Link
            href={`/games/${item.game.bgg_id}`}
            className="text-indigo-300 hover:underline"
          >
            {item.game.primary_name}
          </Link>
        </p>
      </div>
    </article>
  );
}

function CommunityFeed({ state }: { state: Loadable<FeedActivity[]> }) {
  return (
    <section className={cardClass}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2>Weeple Community Feed</h2>

        <Link
          href="/community"
          className="text-sm font-medium text-indigo-400 hover:text-indigo-300 hover:underline"
        >
          View Community →
        </Link>
      </div>

      <StatusMessage
        loading={state.loading}
        error={state.error}
        empty={state.data.length === 0}
        loadingText="Loading community activity..."
        emptyText="No community activity yet. Connect with friends or log a play to get started."
      />

      {!state.loading &&
        !state.error &&
        state.data.map((item) => (
          <FeedActivityItem key={item.id} item={item} />
        ))}
    </section>
  );
}

function FriendItem({ friend }: { friend: Friend }) {
  return (
    <div className="mb-2 flex items-center gap-3 rounded-lg bg-[#0F172A] p-2">
      <div
        aria-hidden="true"
        className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold"
      >
        {friend.display_name.charAt(0).toUpperCase() || "?"}
      </div>

      <span className="font-medium">{friend.display_name}</span>
    </div>
  );
}

function Members({ state }: { state: Loadable<Friend[]> }) {
  return (
    <section className={cardClass}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2>Members</h2>

        <Link
          href="/community"
          className="text-sm font-medium text-indigo-400 hover:text-indigo-300 hover:underline"
        >
          View Weeple →
        </Link>
      </div>

      <StatusMessage
        loading={state.loading}
        error={state.error}
        empty={state.data.length === 0}
        loadingText="Loading friends..."
        emptyText="No friends yet. Visit Weeple to connect with other players."
      />

      {!state.loading &&
        !state.error &&
        state.data.map((friend) => (
          <FriendItem key={friend.user_id} friend={friend} />
        ))}
    </section>
  );
}

export default function Page() {
  const plays = useApiList("/api/v1/plays/", isPlay);
  const feed = useApiList("/api/v1/community/feed/?limit=5", isFeedActivity);
  const friends = useApiList("/api/v1/friends/", isFriend);

  return (
    <div className="min-h-screen bg-[#0F172A] text-[#F8FAFC]">
      <DashboardNavbar />

      <main className="p-4 sm:p-8">
        <h1 className="text-4xl font-extrabold tracking-tight text-white">
          Welcome to QuestLog
        </h1>

        <p className="mb-6 text-gray-400">Your shared activity hub</p>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <RecentlyPlayed state={plays} />
          <PlayCalendar plays={plays.data} />
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <RecentPlays state={plays} />
          <CommunityFeed state={feed} />
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Members state={friends} />

          {/* RECOMMENDED */}
          <div className="bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg transition duration-300 hover:shadow-xl hover:shadow-indigo-500/10">
            <RecommendationStrip
              title="Recommended for you"
              query={{ strategy: "for_you", limit: 4 }}
              emptyMessage="Log a few plays or like some games to get suggestions."
            />
          </div>
        </div>
      </main>
    </div>
  );
}
