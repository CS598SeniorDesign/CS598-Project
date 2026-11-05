/**
 * Client for the backend recommendation engine (/api/v1/recommendations/).
 *
 * Every request goes through the same-origin proxy with the session cookie,
 * and writes send the CSRF token allauth sets in the csrf_token cookie.
 */

export interface RecommendedGame {
  bgg_id: number;
  item_type?: string;
  primary_name: string;
  year_published: number | null;
  thumbnail_url: string | null;
  average_rating: number | string | null;
  bgg_rank: number | null;
}

export interface Recommendation {
  game: RecommendedGame;
  score: number;
  reason: string;
}

export interface RecommendationResponse {
  requested_strategy: string;
  strategy: string;
  personalized: boolean;
  fallback_reason: string | null;
  results: Recommendation[];
}

export interface StrategyOption {
  key: string;
  label: string;
  description: string;
  requires_personal_data: boolean;
  parameters: string[];
}

export interface Choice {
  key: string;
  label: string;
}

export interface NamedTag {
  bgg_id: number;
  name: string;
}

export interface RecommendationOptions {
  strategies: StrategyOption[];
  periods: Choice[];
  complexities: Choice[];
  moods: Choice[];
  categories: NamedTag[];
  mechanics: NamedTag[];
}

export interface RecommendationProfile {
  use_personal_data: boolean;
  preferred_categories: number[];
  preferred_mechanics: number[];
  preferred_player_count: number | null;
  preferred_max_play_time: number | null;
  preferred_complexity: string | number | null;
  updated_at?: string;
}

export type Sentiment = "LIKE" | "DISLIKE";

export interface RecommendationFeedback {
  game: RecommendedGame;
  sentiment: Sentiment;
  strategy: string;
  created_at: string;
  updated_at: string;
}

/** Query values for GET /recommendations/. Empty values are left out. */
export type RecommendationQuery = Record<
  string,
  string | number | boolean | null | undefined
>;

/** Strategies with a UI of their own rather than a spot in the strategy list. */
export const DEDICATED_STRATEGIES = new Set([
  "decision_chart",
  "similar_games",
]);

/** User-facing text for the backend's fallback_reason codes. */
export const FALLBACK_MESSAGES: Record<string, string> = {
  opt_in_required:
    "Turn on personalized recommendations in Preferences to use this. Showing popular picks instead.",
  not_enough_data:
    "We don't know enough about your taste yet. Log some plays or like a few games. Showing popular picks instead.",
};

const BASE_URL = "/api/v1/recommendations";

export class RecommendationApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "RecommendationApiError";
  }
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;

  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));

  return cookie
    ? decodeURIComponent(cookie.split("=").slice(1).join("="))
    : null;
}

function getCsrfToken(): string | null {
  return getCookie("csrf_token") ?? getCookie("csrftoken");
}

function errorMessage(status: number, body: unknown): string {
  if (status === 401 || status === 403) {
    return "Please log in to see recommendations.";
  }
  if (status === 429) {
    return "You're asking for recommendations too quickly. Please wait a moment and try again.";
  }
  if (status === 400 && body && typeof body === "object") {
    const messages = Object.values(body as Record<string, unknown>).flat();
    if (messages.length > 0) {
      return messages.map(String).join(" ");
    }
  }
  return "Unable to load recommendations. Please try again.";
}

async function request<T>(
  path: string,
  init: RequestInit & { signal?: AbortSignal } = {},
): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> | undefined),
  };

  if (method !== "GET") {
    const csrfToken = getCsrfToken();
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
    if (init.body) headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    method,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new RecommendationApiError(
      errorMessage(response.status, body),
      response.status,
    );
  }

  return body as T;
}

/**
 * Build the query string for GET /recommendations/, dropping empty values and
 * false booleans so the backend applies its own defaults.
 */
export function buildRecommendationQuery(query: RecommendationQuery): string {
  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(query)) {
    if (
      value === null ||
      value === undefined ||
      value === "" ||
      value === false
    ) {
      continue;
    }
    params.set(key, String(value));
  }

  return params.toString();
}

export function fetchRecommendations(
  query: RecommendationQuery,
  signal?: AbortSignal,
): Promise<RecommendationResponse> {
  const queryString = buildRecommendationQuery(query);
  return request<RecommendationResponse>(
    `/${queryString ? `?${queryString}` : ""}`,
    { signal },
  );
}

export function fetchRecommendationOptions(
  signal?: AbortSignal,
): Promise<RecommendationOptions> {
  return request<RecommendationOptions>("/options/", { signal });
}

export function fetchRecommendationProfile(
  signal?: AbortSignal,
): Promise<RecommendationProfile> {
  return request<RecommendationProfile>("/profile/", { signal });
}

export function updateRecommendationProfile(
  changes: Partial<RecommendationProfile>,
): Promise<RecommendationProfile> {
  return request<RecommendationProfile>("/profile/", {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export async function fetchRecommendationFeedback(
  signal?: AbortSignal,
): Promise<RecommendationFeedback[]> {
  const data = await request<
    RecommendationFeedback[] | { results: RecommendationFeedback[] }
  >("/feedback/", { signal });

  return Array.isArray(data) ? data : data.results;
}

export function sendRecommendationFeedback(
  gameId: number,
  sentiment: Sentiment,
  strategy?: string,
): Promise<RecommendationFeedback> {
  return request<RecommendationFeedback>("/feedback/", {
    method: "POST",
    body: JSON.stringify({
      game_id: gameId,
      sentiment,
      ...(strategy ? { strategy } : {}),
    }),
  });
}

export function removeRecommendationFeedback(gameId: number): Promise<void> {
  return request<void>(`/feedback/${gameId}/`, { method: "DELETE" });
}
