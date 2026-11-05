import "@testing-library/jest-dom";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import RatingEditor from "./RatingEditor";
import { deleteRating, saveRating, type Rating } from "@/lib/ratings";

jest.mock("@/lib/ratings", () => ({
  ...jest.requireActual("@/lib/ratings"),
  saveRating: jest.fn(),
  deleteRating: jest.fn(),
}));

const mockSave = saveRating as jest.Mock;
const mockDelete = deleteRating as jest.Mock;

const existing: Rating = {
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
  enjoyment: 4,
  overall_rating: 4,
};

function pick(dimension: string, stars: number) {
  const group = screen.getByRole("group", { name: dimension });
  fireEvent.click(
    within(group).getByRole("radio", {
      name: `${stars} ${stars === 1 ? "star" : "stars"}`,
    }),
  );
}

beforeEach(() => {
  mockSave.mockReset();
  mockDelete.mockReset();
});

describe("RatingEditor", () => {
  it("needs a score for every dimension before saving", async () => {
    const onSaved = jest.fn();
    mockSave.mockResolvedValue(existing);
    render(
      <RatingEditor
        gameId={13}
        gameName="Catan"
        rating={null}
        onSaved={onSaved}
      />,
    );

    const save = screen.getByRole("button", { name: "Save rating" });
    expect(save).toBeDisabled();

    pick("Experience", 4);
    pick("Mechanics", 3);
    pick("Replayability", 5);
    expect(save).toBeDisabled();
    pick("Enjoyment", 4);

    expect(screen.getByText("★ 4.0 / 5")).toBeInTheDocument();
    fireEvent.click(save);

    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(existing));
    expect(mockSave).toHaveBeenCalledWith(
      13,
      { experience: 4, mechanics: 3, replayability: 5, enjoyment: 4 },
      false,
    );
  });

  it("starts from the existing rating and edits it", async () => {
    const onSaved = jest.fn();
    mockSave.mockResolvedValue({ ...existing, enjoyment: 2 });
    render(
      <RatingEditor
        gameId={13}
        gameName="Catan"
        rating={existing}
        onSaved={onSaved}
      />,
    );

    const enjoyment = screen.getByRole("group", { name: "Enjoyment" });
    expect(
      within(enjoyment).getByRole("radio", { name: "4 stars" }),
    ).toBeChecked();

    pick("Enjoyment", 2);
    fireEvent.click(screen.getByRole("button", { name: "Save rating" }));

    await waitFor(() =>
      expect(mockSave).toHaveBeenCalledWith(
        13,
        { experience: 4, mechanics: 3, replayability: 5, enjoyment: 2 },
        true,
      ),
    );
  });

  it("deletes a rating", async () => {
    const onSaved = jest.fn();
    mockDelete.mockResolvedValue(undefined);
    render(
      <RatingEditor
        gameId={13}
        gameName="Catan"
        rating={existing}
        onSaved={onSaved}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete rating" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(null));
    expect(mockDelete).toHaveBeenCalledWith(13);
  });

  it("shows an error when saving fails", async () => {
    mockSave.mockRejectedValue(new Error("Please log in to rate games."));
    render(
      <RatingEditor
        gameId={13}
        gameName="Catan"
        rating={existing}
        onSaved={jest.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Save rating" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Please log in to rate games.",
    );
  });
});
