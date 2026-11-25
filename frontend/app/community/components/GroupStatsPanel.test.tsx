import "@testing-library/jest-dom";
import { render, screen, within } from "@testing-library/react";
import GroupStatsPanel from "./GroupStatsPanel";
import { fetchGroupStatistics, type GroupStatistics } from "@/lib/analytics";

jest.mock("@/lib/analytics", () => ({
  ...jest.requireActual("@/lib/analytics"),
  fetchGroupStatistics: jest.fn(),
}));

jest.mock("recharts", () => {
  const actual = jest.requireActual("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 400, height: 200 }}>{children}</div>
    ),
  };
});

const mockFetchGroupStatistics = fetchGroupStatistics as jest.Mock;

const statistics: GroupStatistics = {
  group_id: 7,
  group_name: "Friday Night",
  member_count: 3,
  total_sessions: 5,
  total_plays: 6,
  total_play_time_minutes: 315,
  last_played: "2026-11-20",
  most_played_games: [
    { bgg_id: 13, name: "Catan", sessions: 3, plays: 4 },
    { bgg_id: 822, name: "Carcassonne", sessions: 1, plays: 1 },
  ],
  leaderboard: [
    {
      player: { user_id: "user-1", display_name: "Morgan" },
      sessions: 5,
      wins: 3,
      win_rate: 60,
    },
    {
      player: { user_id: "user-2", display_name: "Pat" },
      sessions: 4,
      wins: 1,
      win_rate: 25,
    },
    {
      player: { user_id: "user-3", display_name: "Riley" },
      sessions: 0,
      wins: 0,
      win_rate: null,
    },
  ],
  monthly_activity: [
    { month: "2026-10", sessions: 2, plays: 2 },
    { month: "2026-11", sessions: 3, plays: 4 },
  ],
};

beforeEach(() => {
  mockFetchGroupStatistics.mockReset();
});

describe("GroupStatsPanel", () => {
  it("shows the group's totals, leaderboard and top games", async () => {
    mockFetchGroupStatistics.mockResolvedValue(statistics);

    render(<GroupStatsPanel groupId={7} />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading group stats...",
    );
    const leaderboard = await screen.findByRole("list", {
      name: "Leaderboard",
    });
    expect(mockFetchGroupStatistics).toHaveBeenCalledWith(
      7,
      expect.any(AbortSignal),
    );

    expect(screen.getByText("5h 15m")).toBeInTheDocument();

    const standings = within(leaderboard).getAllByRole("listitem");
    expect(standings).toHaveLength(3);
    expect(within(standings[0]).getByText("Morgan")).toBeInTheDocument();
    expect(within(standings[0]).getByLabelText("First place")).toBeVisible();
    expect(within(standings[0]).getByText("60.0%")).toBeInTheDocument();
    expect(within(standings[1]).getByText("2")).toBeInTheDocument();
    expect(within(standings[1]).getByText("1 win · 4 games")).toBeVisible();
    expect(within(standings[2]).getByText("N/A")).toBeInTheDocument();

    expect(screen.getByText("Top Games")).toBeInTheDocument();
    expect(screen.getByText("Carcassonne")).toBeInTheDocument();
    expect(screen.getByText("Last 12 Months")).toBeInTheDocument();
  });

  it("leaves the trophy off when nobody has won yet", async () => {
    mockFetchGroupStatistics.mockResolvedValue({
      ...statistics,
      leaderboard: statistics.leaderboard.map((standing) => ({
        ...standing,
        wins: 0,
        win_rate: 0,
      })),
    });

    render(<GroupStatsPanel groupId={7} />);

    await screen.findByRole("list", { name: "Leaderboard" });
    expect(screen.queryByLabelText("First place")).not.toBeInTheDocument();
  });

  it("explains when no games have been logged for the group", async () => {
    mockFetchGroupStatistics.mockResolvedValue({
      ...statistics,
      total_sessions: 0,
      total_plays: 0,
      total_play_time_minutes: 0,
      last_played: null,
      most_played_games: [],
    });

    render(<GroupStatsPanel groupId={7} />);

    expect(
      await screen.findByText("No games have been logged for this group yet."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("list", { name: "Leaderboard" }),
    ).not.toBeInTheDocument();
  });

  it("shows the error when the statistics cannot be loaded", async () => {
    mockFetchGroupStatistics.mockRejectedValue(
      new Error("Statistics for this group are not available."),
    );

    render(<GroupStatsPanel groupId={7} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Statistics for this group are not available.",
    );
  });
});
