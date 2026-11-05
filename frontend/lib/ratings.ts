/**
 * Client for the user's own ratings of games (/api/v1/ratings/).
 *
 * A rating is four scores from 1 to 5; the backend adds overall_rating, their
 * average. Ratings are private and addressed by the game's BGG ID.
 */

import { ApiError, apiRequest, drfMessages } from "@/lib/api";
import type { LibraryGame } from "@/lib/library";

export const RATING_DIMENSIONS = [
  {
    key: "experience",
    label: "Experience",
    hint: "How the game felt to play",
  },
  { key: "mechanics", label: "Mechanics", hint: "How well the rules work" },
  {
    key: "replayability",
    label: "Replayability",
    hint: "Would you play it again and again?",
  },
  { key: "enjoyment", label: "Enjoyment", hint: "How much fun you had" },
] as const;

export type RatingDimension = (typeof RATING_DIMENSIONS)[number]["key"];

export type RatingScores = Record<RatingDimension, number>;

export interface Rating extends RatingScores {
  game: LibraryGame;
  overall_rating: number;
}

export const MIN_SCORE = 1;
export const MAX_SCORE = 5;

const BASE_URL = "/api/v1/ratings";

function describeRatingError(status: number, body: unknown): string {
  if (status === 401 || status === 403) {
    return "Please log in to rate games.";
  }
  if (status === 404) {
    return "You haven't rated this game yet.";
  }
  if (status === 400 || status === 409) {
    const messages = drfMessages(body).filter(
      (message) => !message.startsWith("http"),
    );
    if (messages.length > 0) return messages.join(" ");
  }
  return "Unable to save your rating. Please try again.";
}

function request<T>(path: string, init?: RequestInit): Promise<T> {
  return apiRequest<T>(`${BASE_URL}${path}`, init, describeRatingError);
}

/** Format an overall rating, e.g. 4.25 -> "4.3". */
export function formatOverall(value: number): string {
  return value.toFixed(1);
}

export async function fetchRatings(signal?: AbortSignal): Promise<Rating[]> {
  const data = await request<Rating[] | { results: Rating[] }>("/", {
    signal,
  });
  return Array.isArray(data) ? data : data.results;
}

/** The user's rating of a game, or null when they haven't rated it. */
export async function fetchRating(
  gameId: number,
  signal?: AbortSignal,
): Promise<Rating | null> {
  try {
    return await request<Rating>(`/${gameId}/`, { signal });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

/**
 * Save the user's rating of a game: create it, or edit it when it already
 * exists. A create that finds an existing rating (409, e.g. rated in another
 * tab) is retried as an edit.
 */
export async function saveRating(
  gameId: number,
  scores: RatingScores,
  exists: boolean,
): Promise<Rating> {
  const edit = () =>
    request<Rating>(`/${gameId}/`, {
      method: "PATCH",
      body: JSON.stringify(scores),
    });

  if (exists) return edit();

  try {
    return await request<Rating>("/", {
      method: "POST",
      body: JSON.stringify({ game_id: gameId, ...scores }),
    });
  } catch (err) {
    if (err instanceof ApiError && err.status === 409) return edit();
    throw err;
  }
}

export function deleteRating(gameId: number): Promise<void> {
  return request<void>(`/${gameId}/`, { method: "DELETE" });
}
