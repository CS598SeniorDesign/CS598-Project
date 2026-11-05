"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import WinRateChart from "@/components/stats/WinRateChart";

interface GameSummary {
  bgg_id: number;
  name: string;
  sessions: number;
  plays: number;
  wins: number;
  win_rate: number | null;
}

interface CategorySummary {
  name: string;
  sessions: number;
}

interface MonthlyActivity {
  month: string;
  plays: number;
  wins: number;
}

interface AnalyticsSummary {
  total_sessions: number;
  total_plays: number;
  plays_this_month: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  total_play_time_minutes: number;
  average_session_minutes: number | null;
  games_played: number;
  games_owned: number;
  most_played_games: GameSummary[];
  top_categories: CategorySummary[];
  monthly_activity: MonthlyActivity[];
}

const cardClass = "rounded-2xl bg-[#1E293B] p-6 shadow-lg";

function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;

  if (hours === 0) {
    return `${remaining}m`;
  }

  return remaining === 0 ? `${hours}h` : `${hours}h ${remaining}m`;
}

function formatPercent(value: number | null): string {
  return value === null ? "N/A" : `${value.toFixed(1)}%`;
}

function getAnalyticsErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unable to load analytics.";
}

function getResponseError(status: number): string {
  if (status === 401 || status === 403) {
    return "Please log in to view your analytics.";
  }

  return `Unable to load analytics (${status}).`;
}

function StatCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail?: string;
}) {
  return (
    <div className="rounded-xl bg-[#0F172A] p-5 text-center">
      <p className="mb-2 text-sm text-gray-400">{label}</p>

      <p className="text-2xl font-bold text-indigo-400">{value}</p>

      {detail && <p className="mt-2 text-xs text-gray-400">{detail}</p>}
    </div>
  );
}

function AnalyticsStats({ data }: { data: AnalyticsSummary }) {
  const completedSessions = data.wins + data.losses;

  const averageDuration =
    data.average_session_minutes === null
      ? "No session durations recorded"
      : `Avg. ${formatDuration(
          Math.round(data.average_session_minutes),
        )} per timed session`;

  return (
    <section className={cardClass}>
      <h2 className="mb-5 text-xl font-semibold">Your Stats</h2>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        <StatCard
          label="Total Plays"
          value={data.total_plays}
          detail={`${data.plays_this_month} this month`}
        />

        <StatCard
          label="Win Rate"
          value={formatPercent(data.win_rate)}
          detail={`${completedSessions} completed sessions`}
        />

        <StatCard label="Owned Games" value={data.games_owned} />

        <StatCard label="Total Sessions" value={data.total_sessions} />

        <StatCard label="Wins" value={data.wins} />

        <StatCard label="Losses" value={data.losses} />

        <StatCard label="Games Played" value={data.games_played} />

        <StatCard
          label="Total Playtime"
          value={formatDuration(data.total_play_time_minutes)}
          detail={averageDuration}
        />
      </div>
    </section>
  );
}

function WinRateSection({ data }: { data: AnalyticsSummary }) {
  const completedSessions = data.wins + data.losses;

  const chartData = [
    { label: "Wins", value: data.wins },
    { label: "Losses", value: data.losses },
  ];

  return (
    <section className={cardClass}>
      <h2 className="mb-4 text-xl font-semibold">Win Rate</h2>

      {completedSessions === 0 ? (
        <p className="py-16 text-center text-gray-400">
          Complete a game session to see your win rate.
        </p>
      ) : (
        <div className="flex flex-col items-center">
          <WinRateChart className="flex justify-center" data={chartData} />

          <p className="text-sm text-gray-400">
            {data.wins} wins · {data.losses} losses
          </p>
        </div>
      )}
    </section>
  );
}

function CategorySection({ categories }: { categories: CategorySummary[] }) {
  const maxSessions = Math.max(
    1,
    ...categories.map((category) => category.sessions),
  );

  if (categories.length === 0) {
    return (
      <section className={cardClass}>
        <h2 className="mb-4 text-xl font-semibold">Favorite Game Categories</h2>

        <p className="py-16 text-center text-gray-400">
          Log some plays to discover your favorite categories.
        </p>
      </section>
    );
  }

  return (
    <section className={cardClass}>
      <h2 className="mb-4 text-xl font-semibold">Favorite Game Categories</h2>

      <div className="space-y-5">
        {categories.map((category) => (
          <div key={category.name}>
            <div className="mb-2 flex justify-between gap-3 text-sm">
              <span>{category.name}</span>

              <span className="text-gray-400">
                {category.sessions} sessions
              </span>
            </div>

            <div className="h-3 overflow-hidden rounded-full bg-slate-700">
              <div
                className="h-full rounded-full bg-indigo-500"
                style={{
                  width: `${(category.sessions / maxSessions) * 100}%`,
                }}
              />
            </div>
          </div>
        ))}

        <p className="text-xs text-gray-400">
          Games can belong to multiple categories.
        </p>
      </div>
    </section>
  );
}

function MonthlyActivitySection({ activity }: { activity: MonthlyActivity[] }) {
  const chartData = activity.map((item) => ({
    ...item,
    label: item.month,
  }));

  return (
    <section className={`mt-6 ${cardClass}`}>
      <h2 className="mb-2 text-xl font-semibold">Gameplay Activity</h2>

      <p className="mb-6 text-sm text-gray-400">
        Your recorded plays over the last 12 months
      </p>

      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#334155"
              vertical={false}
            />

            <XAxis
              dataKey="label"
              stroke="#94A3B8"
              tick={{ fontSize: 11 }}
              tickFormatter={(value: string) => value.slice(5)}
            />

            <YAxis stroke="#94A3B8" allowDecimals={false} />

            <Tooltip
              contentStyle={{
                backgroundColor: "#0F172A",
                border: "1px solid #334155",
                borderRadius: 12,
              }}
            />

            <Bar
              dataKey="plays"
              name="Plays"
              fill="#4F46E5"
              radius={[5, 5, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function MostPlayedGamesSection({ games }: { games: GameSummary[] }) {
  return (
    <section className={`mt-6 ${cardClass}`}>
      <h2 className="mb-5 text-xl font-semibold">Most Played Games</h2>

      {games.length === 0 ? (
        <p className="text-gray-400">
          No games played yet. Start logging your sessions!
        </p>
      ) : (
        <div className="space-y-3">
          {games.map((game, index) => (
            <Link
              key={game.bgg_id}
              href={`/games/${game.bgg_id}`}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-[#0F172A] p-4 transition hover:bg-slate-800"
            >
              <div className="flex items-center gap-4">
                <span className="text-lg font-bold text-indigo-400">
                  #{index + 1}
                </span>

                <div>
                  <p className="font-semibold">{game.name}</p>

                  <p className="text-sm text-gray-400">
                    {game.sessions} sessions · {game.plays} plays
                  </p>
                </div>
              </div>

              <span className="text-sm text-emerald-400">
                {formatPercent(game.win_rate)} win rate
              </span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}

function AnalyticsContent({ data }: { data: AnalyticsSummary }) {
  return (
    <>
      <AnalyticsStats data={data} />

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <WinRateSection data={data} />

        <CategorySection categories={data.top_categories} />
      </div>

      <MonthlyActivitySection activity={data.monthly_activity} />

      <MostPlayedGamesSection games={data.most_played_games} />
    </>
  );
}

function AnalyticsResult({
  loading,
  error,
  summary,
}: {
  loading: boolean;
  error: string;
  summary: AnalyticsSummary | null;
}) {
  if (loading) {
    return <p className="text-gray-400">Loading your analytics...</p>;
  }

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-red-500/30 bg-red-950/30 p-5 text-red-300"
      >
        {error}
      </div>
    );
  }

  if (!summary) {
    return <p className="text-gray-400">No analytics available.</p>;
  }

  return <AnalyticsContent data={summary} />;
}

async function fetchAnalytics(signal: AbortSignal): Promise<AnalyticsSummary> {
  const response = await fetch("/api/v1/analytics/summary/", {
    credentials: "same-origin",
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error(getResponseError(response.status));
  }

  return (await response.json()) as AnalyticsSummary;
}

function useAnalytics() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const result = await fetchAnalytics(controller.signal);

        if (!controller.signal.aborted) {
          setSummary(result);
        }
      } catch (caught) {
        if (!controller.signal.aborted) {
          setError(getAnalyticsErrorMessage(caught));
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

  return { summary, loading, error };
}

export default function AnalyticsPage() {
  const { summary, loading, error } = useAnalytics();

  return (
    <main className="min-h-screen bg-[#0F172A] p-8 text-[#F8FAFC]">
      <h1 className="mb-2 text-4xl font-bold">Your Analytics</h1>

      <p className="mb-8 text-gray-400">
        Explore your real gameplay statistics, win rates, and activity.
      </p>

      <AnalyticsResult loading={loading} error={error} summary={summary} />
    </main>
  );
}
