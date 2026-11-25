"use client";

import { useEffect, useState } from "react";
import { Trophy } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  fetchGroupStatistics,
  formatPlayDate,
  formatPlayTime,
  formatWinRate,
  type GroupMonth,
  type GroupStanding,
  type GroupStatistics,
} from "@/lib/analytics";

interface GroupStatisticsResult {
  groupId: number;
  statistics: GroupStatistics | null;
  error: string;
}

/**
 * Load a group's statistics. The result is kept with the group ID it was
 * loaded for, so switching groups shows loading until the new one lands.
 */
function useGroupStatistics(groupId: number) {
  const [result, setResult] = useState<GroupStatisticsResult | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchGroupStatistics(groupId, controller.signal)
      .then((statistics) => {
        if (!controller.signal.aborted) {
          setResult({ groupId, statistics, error: "" });
        }
      })
      .catch((caughtError: unknown) => {
        if (!controller.signal.aborted) {
          setResult({
            groupId,
            statistics: null,
            error:
              caughtError instanceof Error
                ? caughtError.message
                : "Unable to load statistics. Please try again.",
          });
        }
      });

    return () => controller.abort();
  }, [groupId]);

  return result?.groupId === groupId ? result : null;
}

function StatTile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-border bg-background p-4 text-center">
      <p className="mb-1 text-xs text-muted">{label}</p>

      <p className="text-xl font-bold text-link">{value}</p>
    </div>
  );
}

function Leaderboard({ standings }: { standings: GroupStanding[] }) {
  return (
    <div>
      <h4 className="mb-3 font-semibold text-foreground">Leaderboard</h4>

      <ol aria-label="Leaderboard" className="space-y-2">
        {standings.map((standing, index) => (
          <li
            key={standing.player.user_id}
            className="flex items-center justify-between gap-3 rounded-xl border border-border bg-background px-4 py-3"
          >
            <div className="flex min-w-0 items-center gap-3">
              <span className="w-6 text-center text-lg font-bold text-link">
                {index === 0 && standing.wins > 0 ? (
                  <Trophy
                    aria-label="First place"
                    className="mx-auto h-5 w-5 text-amber-300 [html[data-theme=light]_&]:text-amber-600"
                  />
                ) : (
                  index + 1
                )}
              </span>

              <div className="min-w-0">
                <p className="truncate font-medium text-foreground">
                  {standing.player.display_name}
                </p>

                <p className="text-xs text-muted">
                  {standing.wins} {standing.wins === 1 ? "win" : "wins"} ·{" "}
                  {standing.sessions}{" "}
                  {standing.sessions === 1 ? "game" : "games"}
                </p>
              </div>
            </div>

            <span className="text-sm font-semibold text-subtle">
              {formatWinRate(standing.win_rate)}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function ActivityChart({ activity }: { activity: GroupMonth[] }) {
  return (
    <div>
      <h4 className="mb-3 font-semibold text-foreground">Last 12 Months</h4>

      <div className="h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={activity}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              vertical={false}
            />

            <XAxis
              dataKey="month"
              stroke="var(--muted)"
              tick={{ fontSize: 11, fill: "var(--muted)" }}
              tickFormatter={(value: string) => value.slice(5)}
            />

            <YAxis
              stroke="var(--muted)"
              tick={{ fill: "var(--muted)" }}
              allowDecimals={false}
              width={28}
            />

            <Tooltip
              cursor={{ fill: "var(--surface-hover)" }}
              contentStyle={{
                backgroundColor: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                color: "var(--foreground)",
              }}
              labelStyle={{ color: "var(--foreground)" }}
              itemStyle={{ color: "var(--foreground)" }}
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
    </div>
  );
}

function GroupStatisticsContent({
  statistics,
}: {
  statistics: GroupStatistics;
}) {
  if (statistics.total_sessions === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-background p-6 text-center">
        <p className="text-subtle">
          No games have been logged for this group yet.
        </p>

        <p className="mt-2 text-sm text-muted">
          Choose this group when you log a play to track it here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3">
        <StatTile label="Games logged" value={statistics.total_sessions} />

        <StatTile label="Total plays" value={statistics.total_plays} />

        <StatTile
          label="Playtime"
          value={formatPlayTime(statistics.total_play_time_minutes)}
        />

        <StatTile
          label="Last played"
          value={
            statistics.last_played
              ? formatPlayDate(statistics.last_played)
              : "N/A"
          }
        />
      </div>

      <Leaderboard standings={statistics.leaderboard} />

      {statistics.most_played_games.length > 0 && (
        <div>
          <h4 className="mb-3 font-semibold text-foreground">Top Games</h4>

          <ul className="space-y-2">
            {statistics.most_played_games.map((game) => (
              <li
                key={game.bgg_id}
                className="flex items-center justify-between gap-3 rounded-xl border border-border bg-background px-4 py-3"
              >
                <span className="truncate font-medium text-foreground">
                  {game.name}
                </span>

                <span className="shrink-0 text-xs text-muted">
                  {game.sessions} {game.sessions === 1 ? "game" : "games"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <ActivityChart activity={statistics.monthly_activity} />
    </div>
  );
}

/**
 * A group's statistics from the games logged for it: totals, a leaderboard of
 * current members, the most played games and plays per month.
 */
export default function GroupStatsPanel({ groupId }: { groupId: number }) {
  const result = useGroupStatistics(groupId);

  if (result === null) {
    return (
      <p role="status" className="text-sm text-muted">
        Loading group stats...
      </p>
    );
  }

  if (result.error || result.statistics === null) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-300 [html[data-theme=light]_&]:text-red-700"
      >
        {result.error}
      </div>
    );
  }

  return <GroupStatisticsContent statistics={result.statistics} />;
}
