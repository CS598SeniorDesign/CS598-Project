import "@testing-library/jest-dom";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import LibraryPage from "./page";
import {
  fetchLibrary,
  fetchLibrarySummary,
  updateLibraryItem,
  type LibraryItem,
} from "@/lib/library";

jest.mock("@/lib/ratings", () => ({
  ...jest.requireActual("@/lib/ratings"),
  fetchRatings: jest.fn().mockResolvedValue([]),
}));

jest.mock("@/lib/library", () => ({
  ...jest.requireActual("@/lib/library"),
  fetchLibrary: jest.fn(),
  fetchLibrarySummary: jest.fn(),
  updateLibraryItem: jest.fn(),
}));

const mockFetchLibrary = fetchLibrary as jest.Mock;
const mockSummary = fetchLibrarySummary as jest.Mock;
const mockUpdate = updateLibraryItem as jest.Mock;

function makeItem(
  bggId: number,
  name: string,
  overrides: Partial<LibraryItem> = {},
): LibraryItem {
  return {
    game: {
      bgg_id: bggId,
      primary_name: name,
      year_published: 2020,
      thumbnail_url: null,
      average_rating: "7.0",
      bgg_rank: 100,
    },
    ownership: "OWNED",
    is_played: false,
    has_played: false,
    play_count: 0,
    last_played: null,
    wishlist_priority: null,
    house_rules: "",
    added_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  mockFetchLibrary.mockReset();
  mockUpdate.mockReset();
  mockSummary.mockResolvedValue({
    owned: 2,
    wishlisted: 1,
    owned_unplayed: 1,
    wishlisted_unplayed: 1,
    total: 3,
  });
});

describe("LibraryPage", () => {
  it("lists owned games with counts on the tabs", async () => {
    mockFetchLibrary.mockResolvedValue([
      makeItem(1, "Azul"),
      makeItem(2, "Root"),
    ]);

    render(<LibraryPage />);

    expect(await screen.findByText("Azul")).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: "Library (2)" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: "Wishlist (1)" }),
    ).toBeInTheDocument();
    expect(mockFetchLibrary).toHaveBeenCalledWith(
      { ownership: "OWNED", played: "all", ordering: "-added_at" },
      expect.anything(),
    );
  });

  it("loads the wishlist with its own sort options", async () => {
    mockFetchLibrary.mockResolvedValue([]);
    render(<LibraryPage />);
    await screen.findByText(/Your library is empty/);

    fireEvent.click(screen.getByRole("tab", { name: /Wishlist/ }));

    expect(
      await screen.findByText("Your wishlist is empty for now."),
    ).toBeInTheDocument();
    expect(mockFetchLibrary).toHaveBeenLastCalledWith(
      expect.objectContaining({ ownership: "WISHLISTED" }),
      expect.anything(),
    );
    expect(
      screen.getByRole("option", { name: "Priority" }),
    ).toBeInTheDocument();
  });

  it("sends the played filter and sort order to the API", async () => {
    mockFetchLibrary.mockResolvedValue([]);
    render(<LibraryPage />);
    await screen.findByText(/Your library is empty/);

    fireEvent.change(screen.getByLabelText("Filter by played"), {
      target: { value: "unplayed" },
    });
    fireEvent.change(screen.getByLabelText("Sort by"), {
      target: { value: "-play_count" },
    });

    await waitFor(() =>
      expect(mockFetchLibrary).toHaveBeenLastCalledWith(
        expect.objectContaining({
          played: "unplayed",
          ordering: "-play_count",
        }),
        expect.anything(),
      ),
    );
    expect(
      await screen.findByText("No games match your search."),
    ).toBeInTheDocument();
  });

  it("searches after the user stops typing", async () => {
    jest.useFakeTimers();
    try {
      mockFetchLibrary.mockResolvedValue([]);
      render(<LibraryPage />);

      fireEvent.change(
        screen.getByPlaceholderText("Search your collection..."),
        {
          target: { value: "cat" },
        },
      );
      expect(mockFetchLibrary).not.toHaveBeenCalledWith(
        expect.objectContaining({ search: "cat" }),
        expect.anything(),
      );

      await act(async () => {
        jest.advanceTimersByTime(300);
      });

      expect(mockFetchLibrary).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: "cat" }),
        expect.anything(),
      );
    } finally {
      jest.useRealTimers();
    }
  });

  it("drops a game from the wishlist view once it moves to the library", async () => {
    const wished = makeItem(3, "Everdell", { ownership: "WISHLISTED" });
    mockFetchLibrary.mockImplementation(async (query) =>
      query.ownership === "WISHLISTED" ? [wished] : [],
    );
    mockUpdate.mockResolvedValue({ ...wished, ownership: "OWNED" });

    render(<LibraryPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Wishlist/ }));
    await screen.findByText("Everdell");

    fireEvent.click(
      screen.getByRole("button", { name: "Got it! Move to library" }),
    );

    await waitFor(() =>
      expect(screen.queryByText("Everdell")).not.toBeInTheDocument(),
    );
    expect(mockUpdate).toHaveBeenCalledWith(3, { ownership: "OWNED" });
  });
});
