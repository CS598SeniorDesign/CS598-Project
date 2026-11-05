import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import RecommendationResults from "./RecommendationResults";
import type { RecommendationResponse } from "@/lib/recommendations";

function game(bggId: number, name: string) {
  return {
    game: {
      bgg_id: bggId,
      primary_name: name,
      year_published: 2020,
      thumbnail_url: null,
      average_rating: "7.5",
      bgg_rank: 10,
    },
    score: 1,
    reason: `Because you liked ${name}`,
  };
}

const response: RecommendationResponse = {
  requested_strategy: "for_you",
  strategy: "for_you",
  personalized: true,
  fallback_reason: null,
  results: [game(1, "Azul"), game(2, "Root")],
};

describe("RecommendationResults", () => {
  it("shows each game with its reason", () => {
    render(
      <RecommendationResults
        response={response}
        loading={false}
        error=""
        feedback={{}}
      />,
    );

    expect(screen.getByText("Azul")).toBeInTheDocument();
    expect(screen.getByText("Because you liked Root")).toBeInTheDocument();
    expect(screen.getByText(/Personalized/)).toBeInTheDocument();
  });

  it("hides disliked games", () => {
    render(
      <RecommendationResults
        response={response}
        loading={false}
        error=""
        feedback={{ 2: "DISLIKE" }}
      />,
    );

    expect(screen.queryByText("Root")).not.toBeInTheDocument();
  });

  it("explains a fallback and links to preferences", () => {
    const openPreferences = jest.fn();
    render(
      <RecommendationResults
        response={{
          ...response,
          strategy: "popular",
          personalized: false,
          fallback_reason: "opt_in_required",
        }}
        loading={false}
        error=""
        feedback={{}}
        onOpenPreferences={openPreferences}
      />,
    );

    expect(screen.getByRole("note")).toHaveTextContent(
      /Turn on personalized recommendations/,
    );
    fireEvent.click(screen.getByRole("button", { name: "Open Preferences" }));
    expect(openPreferences).toHaveBeenCalled();
  });

  it("reports likes with the strategy that produced the game", () => {
    const onFeedback = jest.fn();
    render(
      <RecommendationResults
        response={response}
        loading={false}
        error=""
        feedback={{ 1: "LIKE" }}
        onFeedback={onFeedback}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Like Root" }));
    expect(onFeedback).toHaveBeenCalledWith(2, "LIKE", "for_you");

    // Clicking an active reaction clears it.
    fireEvent.click(screen.getByRole("button", { name: "Like Azul" }));
    expect(onFeedback).toHaveBeenCalledWith(1, null, "for_you");
  });
});
