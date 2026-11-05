import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import DecisionChart from "./DecisionChart";

function choose(label: string | RegExp) {
  fireEvent.click(screen.getByRole("button", { name: label }));
}

describe("DecisionChart", () => {
  it("walks through the questions and reports the answers", () => {
    const onComplete = jest.fn();
    render(<DecisionChart personalized={false} onComplete={onComplete} />);

    expect(
      screen.getByText("How many people are playing?"),
    ).toBeInTheDocument();
    choose(/4 players/);
    expect(screen.getByText("How much time do you have?")).toBeInTheDocument();
    choose(/About an hour/);
    choose(/^Medium/);
    choose(/Work together/);

    expect(onComplete).toHaveBeenCalledWith({
      players: 4,
      max_play_time: 60,
      complexity: "medium",
      mood: "cooperative",
    });
    expect(
      screen.getByText("4 players · About an hour · Medium · Work together"),
    ).toBeInTheDocument();
  });

  it("adapts later questions to earlier answers", () => {
    render(<DecisionChart personalized={false} onComplete={jest.fn()} />);

    choose(/Just me/);
    choose(/30 minutes or less/);

    expect(
      screen.queryByRole("button", { name: /Heavy/ }),
    ).not.toBeInTheDocument();
    choose(/^Light/);
    expect(
      screen.queryByRole("button", { name: /Party/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Big strategy/ }),
    ).not.toBeInTheDocument();
  });

  it("asks about owned games only for opted-in users", () => {
    render(<DecisionChart personalized onComplete={jest.fn()} />);

    expect(screen.getByText("Question 1 of 5")).toBeInTheDocument();
  });

  it("can show games before every question is answered", () => {
    const onComplete = jest.fn();
    render(<DecisionChart personalized={false} onComplete={onComplete} />);

    choose(/2 players/);
    choose(/Show games now/);

    expect(onComplete).toHaveBeenCalledWith({ players: 2 });
  });

  it("goes back without losing earlier answers", () => {
    render(<DecisionChart personalized={false} onComplete={jest.fn()} />);

    choose(/3 players/);
    choose(/Back/);

    expect(screen.getByRole("button", { name: /3 players/ })).toHaveClass(
      "border-indigo-400",
    );
  });
});
