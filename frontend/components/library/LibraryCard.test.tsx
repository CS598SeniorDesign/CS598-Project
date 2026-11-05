import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import LibraryCard from "./LibraryCard";
import type { LibraryItem } from "@/lib/library";

function makeItem(overrides: Partial<LibraryItem> = {}): LibraryItem {
  return {
    game: {
      bgg_id: 13,
      primary_name: "Catan",
      year_published: 1995,
      thumbnail_url: null,
      average_rating: "7.1",
      bgg_rank: 500,
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

function renderCard(item: LibraryItem) {
  const onUpdate = jest.fn().mockResolvedValue(item);
  const onRemove = jest.fn().mockResolvedValue(undefined);
  render(<LibraryCard item={item} onUpdate={onUpdate} onRemove={onRemove} />);
  return { onUpdate, onRemove };
}

describe("LibraryCard", () => {
  it("shows play stats", () => {
    renderCard(
      makeItem({ play_count: 3, has_played: true, last_played: "2026-03-04" }),
    );

    expect(screen.getByText(/3 plays · last/)).toBeInTheDocument();
  });

  it("marks an owned game as played", async () => {
    const { onUpdate } = renderCard(makeItem());

    fireEvent.click(screen.getByLabelText("I've played this"));

    await waitFor(() =>
      expect(onUpdate).toHaveBeenCalledWith(13, { is_played: true }),
    );
  });

  it("locks the played box when plays are logged", () => {
    renderCard(makeItem({ play_count: 2, has_played: true }));

    expect(screen.getByLabelText("I've played this")).toBeDisabled();
    expect(screen.getByLabelText("I've played this")).toBeChecked();
  });

  it("saves house rules", async () => {
    const { onUpdate } = renderCard(makeItem());

    fireEvent.click(
      screen.getByRole("button", { name: "Add house rules for Catan" }),
    );
    fireEvent.change(screen.getByLabelText("House rules for Catan"), {
      target: { value: "  Robber skips the first round  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(onUpdate).toHaveBeenCalledWith(13, {
        house_rules: "Robber skips the first round",
      }),
    );
  });

  it("sets a wishlist priority and moves a game to the library", async () => {
    const { onUpdate } = renderCard(
      makeItem({ ownership: "WISHLISTED", wishlist_priority: 3 }),
    );

    expect(screen.getByText("Like to have")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Priority"), {
      target: { value: "1" },
    });
    await waitFor(() =>
      expect(onUpdate).toHaveBeenCalledWith(13, { wishlist_priority: 1 }),
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Got it! Move to library" }),
    );
    await waitFor(() =>
      expect(onUpdate).toHaveBeenCalledWith(13, { ownership: "OWNED" }),
    );
  });

  it("asks before removing", async () => {
    const { onRemove } = renderCard(makeItem());

    fireEvent.click(screen.getByRole("button", { name: "Remove Catan" }));
    expect(onRemove).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Yes, remove" }));

    await waitFor(() => expect(onRemove).toHaveBeenCalledWith(13));
  });

  it("shows an error when a change fails", async () => {
    const onUpdate = jest.fn().mockRejectedValue(new Error("Nope."));
    render(
      <LibraryCard
        item={makeItem()}
        onUpdate={onUpdate}
        onRemove={jest.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Move to wishlist" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Nope.");
  });

  it("shows the user's rating and opens the rating dialog", () => {
    const onRatingChange = jest.fn();
    render(
      <LibraryCard
        item={makeItem()}
        onUpdate={jest.fn()}
        onRemove={jest.fn()}
        rating={{
          game: makeItem().game,
          experience: 4,
          mechanics: 4,
          replayability: 5,
          enjoyment: 4,
          overall_rating: 4.25,
        }}
        onRatingChange={onRatingChange}
      />,
    );

    expect(screen.getByText("Your rating ★ 4.3 / 5")).toBeInTheDocument();
    expect(screen.getByText("BGG ★ 7.1 / 10")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Edit your rating of Catan" }),
    );
    expect(
      screen.getByRole("heading", { name: "Edit your rating of Catan" }),
    ).toBeInTheDocument();
  });

  it("offers to rate an unrated game", () => {
    render(
      <LibraryCard
        item={makeItem()}
        onUpdate={jest.fn()}
        onRemove={jest.fn()}
        onRatingChange={jest.fn()}
      />,
    );

    expect(screen.getByText("Not rated by you")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Rate Catan" }),
    ).toBeInTheDocument();
  });
});
