/**
 * The "Help me pick a game" decision tree.
 *
 * Each question narrows the backend's decision_chart strategy (players,
 * max_play_time, complexity, mood, owned_only). Earlier answers change which
 * questions and options come next, e.g. a solo player is not offered party
 * games and a 30-minute window is not offered heavy games.
 */

import type { RecommendationQuery } from "@/lib/recommendations";

export type DecisionStepKey =
  "players" | "max_play_time" | "complexity" | "mood" | "owned_only";

export interface DecisionAnswers {
  players?: number;
  max_play_time?: number;
  complexity?: string;
  mood?: string;
  owned_only?: boolean;
}

export interface DecisionOption {
  /** The value sent to the API, or null for "no preference". */
  value: string | number | boolean | null;
  label: string;
  hint?: string;
}

export interface DecisionStep {
  key: DecisionStepKey;
  question: string;
  options: DecisionOption[];
}

export interface DecisionContext {
  /** Whether the user has opted in to personalized recommendations. */
  personalized: boolean;
}

const ANY: DecisionOption = { value: null, label: "No preference" };

const PLAYER_OPTIONS: DecisionOption[] = [
  { value: 1, label: "Just me" },
  { value: 2, label: "2 players" },
  { value: 3, label: "3 players" },
  { value: 4, label: "4 players" },
  { value: 5, label: "5 players" },
  { value: 6, label: "6 players" },
];

const TIME_OPTIONS: DecisionOption[] = [
  { value: 30, label: "30 minutes or less", hint: "A quick one" },
  { value: 60, label: "About an hour" },
  { value: 120, label: "Up to 2 hours" },
  { value: 240, label: "All evening" },
];

const COMPLEXITY_OPTIONS: DecisionOption[] = [
  { value: "light", label: "Light", hint: "Easy to teach" },
  { value: "medium", label: "Medium", hint: "Some crunch" },
  { value: "heavy", label: "Heavy", hint: "Brain burner" },
];

const MOOD_OPTIONS: DecisionOption[] = [
  { value: "cooperative", label: "Work together" },
  { value: "competitive", label: "Cutthroat" },
  { value: "party", label: "Party" },
  { value: "strategic", label: "Big strategy" },
  { value: "relaxed", label: "Relaxed" },
];

/** Moods that need an audience; not offered to a solo player. */
const MULTIPLAYER_MOODS = new Set(["competitive", "party"]);
/** Moods that rarely fit a light, short session. */
const DEEP_MOODS = new Set(["strategic"]);

function complexityOptions(answers: DecisionAnswers): DecisionOption[] {
  const shortSession =
    answers.max_play_time !== undefined && answers.max_play_time <= 30;

  return shortSession
    ? COMPLEXITY_OPTIONS.filter((option) => option.value !== "heavy")
    : COMPLEXITY_OPTIONS;
}

function moodOptions(answers: DecisionAnswers): DecisionOption[] {
  return MOOD_OPTIONS.filter((option) => {
    const mood = String(option.value);
    if (answers.players === 1 && MULTIPLAYER_MOODS.has(mood)) return false;
    if (answers.complexity === "light" && DEEP_MOODS.has(mood)) return false;
    if (answers.complexity === "heavy" && mood === "party") return false;
    return true;
  });
}

/**
 * The questions to ask, in order, given the answers so far. Steps whose
 * options depend on earlier answers are recomputed each time.
 */
export function getDecisionSteps(
  answers: DecisionAnswers,
  context: DecisionContext,
): DecisionStep[] {
  const steps: DecisionStep[] = [
    {
      key: "players",
      question: "How many people are playing?",
      options: [...PLAYER_OPTIONS, ANY],
    },
    {
      key: "max_play_time",
      question: "How much time do you have?",
      options: [...TIME_OPTIONS, ANY],
    },
    {
      key: "complexity",
      question: "How heavy a game?",
      options: [...complexityOptions(answers), ANY],
    },
    {
      key: "mood",
      question: "What's the mood?",
      options: [...moodOptions(answers), ANY],
    },
  ];

  // Restricting to owned games reads the user's library, which the backend
  // only allows once they have opted in.
  if (context.personalized) {
    steps.push({
      key: "owned_only",
      question: "Only games you own?",
      options: [
        { value: true, label: "Yes, from my shelf" },
        { value: false, label: "Show me anything" },
      ],
    });
  }

  return steps;
}

/**
 * Record an answer and drop any later answers the new one makes invalid
 * (e.g. "party" after switching to a solo game).
 */
export function answerStep(
  answers: DecisionAnswers,
  key: DecisionStepKey,
  value: DecisionOption["value"],
  context: DecisionContext,
): DecisionAnswers {
  const next: DecisionAnswers = { ...answers };

  if (value === null) {
    delete next[key];
  } else {
    (next as Record<string, unknown>)[key] = value;
  }

  for (const step of getDecisionSteps(next, context)) {
    const current = next[step.key];
    if (current === undefined) continue;

    const stillOffered = step.options.some(
      (option) => option.value === current,
    );
    if (!stillOffered) delete next[step.key];
  }

  return next;
}

/** Turn the answers into GET /recommendations/ query values. */
export function decisionQuery(
  answers: DecisionAnswers,
  limit = 12,
): RecommendationQuery {
  return {
    strategy: "decision_chart",
    limit,
    players: answers.players,
    max_play_time: answers.max_play_time,
    complexity: answers.complexity,
    mood: answers.mood,
    owned_only: answers.owned_only === true ? true : undefined,
  };
}

/** A short summary of the answers, e.g. "4 players · About an hour". */
export function describeAnswers(
  answers: DecisionAnswers,
  context: DecisionContext,
): string {
  const parts = getDecisionSteps(answers, context)
    .map((step) => {
      const value = answers[step.key];
      if (value === undefined) return null;
      return (
        step.options.find((option) => option.value === value)?.label ?? null
      );
    })
    .filter((part): part is string => part !== null);

  return parts.length > 0 ? parts.join(" · ") : "Anything goes";
}
