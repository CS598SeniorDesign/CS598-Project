import "@testing-library/jest-dom";
import { fireEvent, render, screen, within } from "@testing-library/react";
import MyRating from "./MyRating";
import { fetchRating, saveRating, type Rating } from "@/lib/ratings";

jest.mock("@/lib/ratings", () => ({
  ...jest.requireActual("@/lib/ratings"),
  fetchRating: jest.fn(),
  saveRating: jest.fn(),
}));

const mockFetchRating = fetchRating as jest.Mock;
const mockSave = saveRating as jest.Mock;

const rating: Rating = {
  game: {
    bgg_id: 13,
    primary_name: "Catan",
    year_published: 1995,
    thumbnail_url: null,
    average_rating: "7.1",
    bgg_rank: 500,
  },
  experience: 4,
  mechanics: 3,
  replayability: 5,
  enjoyment: 5,
  overall_rating: 4.25,
};

beforeEach(() => {
  mockFetchRating.mockReset();
  mockSave.mockReset();
});

describe("MyRating", () => {
  it("shows the user's rating with each dimension", async () => {
    mockFetchRating.mockResolvedValue(rating);

    render(<MyRating gameId={13} gameName="Catan" />);

    expect(await screen.findByText(/★ 4.3/)).toBeInTheDocument();
    expect(screen.getByText("Replayability")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Edit rating" }),
    ).toBeInTheDocument();
  });

  it("lets the user rate an unrated game", async () => {
    mockFetchRating.mockResolvedValue(null);
    mockSave.mockResolvedValue(rating);

    render(<MyRating gameId={13} gameName="Catan" />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Rate this game" }),
    );

    for (const [dimension, stars] of [
      ["Experience", "4 stars"],
      ["Mechanics", "3 stars"],
      ["Replayability", "5 stars"],
      ["Enjoyment", "5 stars"],
    ]) {
      fireEvent.click(
        within(screen.getByRole("group", { name: dimension })).getByRole(
          "radio",
          { name: stars },
        ),
      );
    }
    fireEvent.click(screen.getByRole("button", { name: "Save rating" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Rating saved.",
    );
    expect(screen.getByText(/★ 4.3/)).toBeInTheDocument();
  });
});
