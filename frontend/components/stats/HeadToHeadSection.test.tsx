import "@testing-library/jest-dom";
import { render, screen, within } from "@testing-library/react";
import HeadToHeadSection from "./HeadToHeadSection";
import { fetchHeadToHead, type HeadToHead } from "@/lib/analytics";

jest.mock("@/lib/analytics", () => ({
  ...jest.requireActual("@/lib/analytics"),
  fetchHeadToHead: jest.fn(),
}));

const mockFetchHeadToHead = fetchHeadToHead as jest.Mock;

const record: HeadToHead = {
  opponent: { user_id: "friend-1", display_name: "Morgan" },
  sessions_together: 6,
  plays_together: 7,
  completed_sessions: 6,
  you_won: 1,
  they_won: 4,
  both_won: 0,
  neither_won: 1,
  your_win_rate: 16.7,
  their_win_rate: 66.7,
  last_played: "2026-11-20",
  games: [
    { bgg_id: 13, name: "Catan", sessions: 4, you_won: 1, they_won: 3 },
    { bgg_id: 822, name: "Carcassonne", sessions: 1, you_won: 0, they_won: 1 },
  ],
};

function tile(label: string) {
  return screen.getByText(label).parentElement as HTMLElement;
}

beforeEach(() => {
  mockFetchHeadToHead.mockReset();
});

describe("HeadToHeadSection", () => {
  it("shows the record against the friend", async () => {
    mockFetchHeadToHead.mockResolvedValue(record);

    render(<HeadToHeadSection userId="friend-1" friendName="Morgan" />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading your record...",
    );
    expect(await screen.findByText("Morgan won")).toBeInTheDocument();
    expect(mockFetchHeadToHead).toHaveBeenCalledWith(
      "friend-1",
      expect.any(AbortSignal),
    );

    expect(within(tile("You won")).getByText("1")).toBeInTheDocument();
    expect(
      within(tile("You won")).getByText("16.7% win rate"),
    ).toBeInTheDocument();
    expect(within(tile("Morgan won")).getByText("4")).toBeInTheDocument();
    expect(
      within(tile("Games together")).getByText("7 plays"),
    ).toBeInTheDocument();

    const games = screen.getAllByRole("listitem");
    expect(games).toHaveLength(2);
    expect(within(games[0]).getByText("Catan")).toBeInTheDocument();
    expect(within(games[1]).getByText("1 game")).toBeInTheDocument();
  });

  it("explains when the two have not played together", async () => {
    mockFetchHeadToHead.mockResolvedValue({
      ...record,
      sessions_together: 0,
      plays_together: 0,
      completed_sessions: 0,
      you_won: 0,
      they_won: 0,
      neither_won: 0,
      your_win_rate: null,
      their_win_rate: null,
      last_played: null,
      games: [],
    });

    render(<HeadToHeadSection userId="friend-1" friendName="Morgan" />);

    expect(
      await screen.findByText("You haven't played together yet."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Log a game with Morgan to start your record."),
    ).toBeInTheDocument();
  });

  it("shows the error when the record cannot be loaded", async () => {
    mockFetchHeadToHead.mockRejectedValue(
      new Error("No statistics are available for this player."),
    );

    render(<HeadToHeadSection userId="friend-1" friendName="Morgan" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No statistics are available for this player.",
    );
  });

  it("loads the new record when the friend changes", async () => {
    mockFetchHeadToHead.mockResolvedValueOnce(record).mockResolvedValueOnce({
      ...record,
      opponent: { user_id: "friend-2", display_name: "Pat" },
    });

    const { rerender } = render(
      <HeadToHeadSection userId="friend-1" friendName="Morgan" />,
    );
    expect(await screen.findByText("Morgan won")).toBeInTheDocument();

    rerender(<HeadToHeadSection userId="friend-2" friendName="Pat" />);

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(await screen.findByText("Pat won")).toBeInTheDocument();
    expect(mockFetchHeadToHead).toHaveBeenLastCalledWith(
      "friend-2",
      expect.any(AbortSignal),
    );
  });
});
