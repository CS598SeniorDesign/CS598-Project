import {
  answerStep,
  decisionQuery,
  describeAnswers,
  getDecisionSteps,
} from "./decisionChart";

const anonymous = { personalized: false };
const optedIn = { personalized: true };

function optionValues(steps: ReturnType<typeof getDecisionSteps>, key: string) {
  return steps.find((step) => step.key === key)?.options.map((o) => o.value);
}

describe("getDecisionSteps", () => {
  it("asks four questions, plus owned games once the user has opted in", () => {
    expect(getDecisionSteps({}, anonymous).map((step) => step.key)).toEqual([
      "players",
      "max_play_time",
      "complexity",
      "mood",
    ]);
    expect(getDecisionSteps({}, optedIn).map((step) => step.key)).toContain(
      "owned_only",
    );
  });

  it("does not offer party or cutthroat games to a solo player", () => {
    const moods = optionValues(
      getDecisionSteps({ players: 1 }, anonymous),
      "mood",
    );

    expect(moods).not.toContain("party");
    expect(moods).not.toContain("competitive");
    expect(moods).toContain("cooperative");
  });

  it("does not offer heavy games for a 30-minute window", () => {
    const complexities = optionValues(
      getDecisionSteps({ max_play_time: 30 }, anonymous),
      "complexity",
    );

    expect(complexities).not.toContain("heavy");
    expect(complexities).toContain("light");
  });

  it("always offers a no-preference option", () => {
    for (const step of getDecisionSteps({}, anonymous)) {
      expect(step.options.some((option) => option.value === null)).toBe(true);
    }
  });
});

describe("answerStep", () => {
  it("drops later answers that the new answer rules out", () => {
    const party = answerStep({ players: 4 }, "mood", "party", anonymous);
    const solo = answerStep(party, "players", 1, anonymous);

    expect(solo).toEqual({ players: 1 });
  });

  it("keeps later answers that still fit", () => {
    const answers = answerStep(
      { players: 4, mood: "cooperative" },
      "players",
      2,
      anonymous,
    );

    expect(answers).toEqual({ players: 2, mood: "cooperative" });
  });

  it("clears an answer when the user picks no preference", () => {
    expect(answerStep({ players: 4 }, "players", null, anonymous)).toEqual({});
  });
});

describe("decisionQuery", () => {
  it("maps answers to the decision_chart strategy's parameters", () => {
    expect(
      decisionQuery(
        {
          players: 3,
          max_play_time: 60,
          complexity: "medium",
          owned_only: true,
        },
        8,
      ),
    ).toEqual({
      strategy: "decision_chart",
      limit: 8,
      players: 3,
      max_play_time: 60,
      complexity: "medium",
      mood: undefined,
      owned_only: true,
    });
  });

  it("leaves out owned_only unless it is true", () => {
    expect(decisionQuery({ owned_only: false }).owned_only).toBeUndefined();
  });
});

describe("describeAnswers", () => {
  it("summarizes the answers with their labels", () => {
    expect(describeAnswers({ players: 2, mood: "relaxed" }, anonymous)).toBe(
      "2 players · Relaxed",
    );
  });

  it("says anything goes when nothing was chosen", () => {
    expect(describeAnswers({}, anonymous)).toBe("Anything goes");
  });
});
