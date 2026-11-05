/**
 * Client for the user's library and wishlist (/api/v1/library/).
 *
 * Entries are addressed by the game's BoardGameGeek ID.
 */

import { ApiError, apiRequest, drfMessages, toQueryString } from "@/lib/api";

export type Ownership = "OWNED" | "WISHLISTED";

export interface LibraryGame {
  bgg_id: number;
  item_type?: string;
  primary_name: string;
  year_published: number | null;
  thumbnail_url: string | null;
  average_rating: number | string | null;
  bgg_rank: number | null;
}

export interface LibraryItem {
  game: LibraryGame;
  ownership: Ownership;
  /** The user's own "I've played this" flag. */
  is_played: boolean;
  /** True when is_played is set or the user has logged a play. */
  has_played: boolean;
  play_count: number;
  last_played: string | null;
  /** 1 (must have) to 5 (don't buy); wishlisted games only. */
  wishlist_priority: number | null;
  house_rules: string;
  added_at: string;
  updated_at: string;
}

export type LibraryItemChanges = Partial<
  Pick<
    LibraryItem,
    "ownership" | "is_played" | "wishlist_priority" | "house_rules"
  >
>;

export interface LibrarySummary {
  owned: number;
  wishlisted: number;
  owned_unplayed: number;
  wishlisted_unplayed: number;
  total: number;
}

export type PlayedFilter = "all" | "played" | "unplayed";

export interface LibraryQuery {
  ownership?: Ownership;
  played?: PlayedFilter;
  search?: string;
  ordering?: string;
}

export type SyncState =
  "queued" | "running" | "retrying" | "succeeded" | "failed";

export interface SyncStatus {
  task_id: string;
  status: SyncState;
  detail: string;
  added?: number;
  updated?: number;
  skipped?: number;
  imported?: number;
}

export const HOUSE_RULES_MAX_LENGTH = 5000;

/** BoardGameGeek's wishlist priorities, as the backend stores them. */
export const WISHLIST_PRIORITIES: { value: number; label: string }[] = [
  { value: 1, label: "Must have" },
  { value: 2, label: "Love to have" },
  { value: 3, label: "Like to have" },
  { value: 4, label: "Thinking about it" },
  { value: 5, label: "Don't buy this" },
];

export function priorityLabel(priority: number | null): string | null {
  return (
    WISHLIST_PRIORITIES.find((option) => option.value === priority)?.label ??
    null
  );
}

/** Sort options for each tab, as `?ordering=` values. */
export const SORT_OPTIONS: Record<
  Ownership,
  { value: string; label: string }[]
> = {
  OWNED: [
    { value: "-added_at", label: "Recently added" },
    { value: "name", label: "Name (A–Z)" },
    { value: "-name", label: "Name (Z–A)" },
    { value: "-rating", label: "Highest rated" },
    { value: "rank", label: "BGG rank" },
    { value: "-play_count", label: "Most played" },
    { value: "play_count", label: "Least played" },
    { value: "-last_played", label: "Recently played" },
    { value: "last_played", label: "Longest since played" },
  ],
  WISHLISTED: [
    { value: "-added_at", label: "Recently added" },
    { value: "priority", label: "Priority" },
    { value: "name", label: "Name (A–Z)" },
    { value: "-rating", label: "Highest rated" },
    { value: "rank", label: "BGG rank" },
  ],
};

/** Sync states after which polling stops. */
export const FINISHED_SYNC_STATES: ReadonlySet<SyncState> = new Set([
  "succeeded",
  "failed",
]);

const BASE_URL = "/api/v1/library";

function describeLibraryError(status: number, body: unknown): string {
  if (status === 401 || status === 403) {
    return "Please log in to view your library.";
  }
  if (status === 404) {
    return "That game is not in your library.";
  }
  if (status === 409) {
    return "This game is already in your library or wishlist.";
  }
  if (status === 429) {
    return "Too many requests. Please wait a moment and try again.";
  }
  if (status === 400) {
    const messages = drfMessages(body);
    if (messages.length > 0) return messages.join(" ");
  }
  return "Unable to update your library. Please try again.";
}

function request<T>(path: string, init?: RequestInit): Promise<T> {
  return apiRequest<T>(`${BASE_URL}${path}`, init, describeLibraryError);
}

const PLAYED_PARAM: Record<PlayedFilter, string | undefined> = {
  all: undefined,
  played: "true",
  unplayed: "false",
};

export function libraryQueryString(query: LibraryQuery): string {
  return toQueryString({
    ownership: query.ownership,
    has_played: PLAYED_PARAM[query.played ?? "all"],
    search: query.search?.trim(),
    ordering: query.ordering,
  });
}

export async function fetchLibrary(
  query: LibraryQuery = {},
  signal?: AbortSignal,
): Promise<LibraryItem[]> {
  const data = await request<LibraryItem[] | { results: LibraryItem[] }>(
    `/${libraryQueryString(query)}`,
    { signal },
  );
  return Array.isArray(data) ? data : data.results;
}

export function fetchLibrarySummary(
  signal?: AbortSignal,
): Promise<LibrarySummary> {
  return request<LibrarySummary>("/summary/", { signal });
}

/** The user's entry for a game, or null when it is not in their library. */
export async function fetchLibraryItem(
  gameId: number,
  signal?: AbortSignal,
): Promise<LibraryItem | null> {
  try {
    return await request<LibraryItem>(`/${gameId}/`, { signal });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}

export function addToLibrary(
  gameId: number,
  ownership: Ownership,
  changes: Omit<LibraryItemChanges, "ownership"> = {},
): Promise<LibraryItem> {
  return request<LibraryItem>("/", {
    method: "POST",
    body: JSON.stringify({ game_id: gameId, ownership, ...changes }),
  });
}

export function updateLibraryItem(
  gameId: number,
  changes: LibraryItemChanges,
): Promise<LibraryItem> {
  return request<LibraryItem>(`/${gameId}/`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export function removeFromLibrary(gameId: number): Promise<void> {
  return request<void>(`/${gameId}/`, { method: "DELETE" });
}

/** Start importing the user's BoardGameGeek collection in the background. */
export function startBggCollectionSync(): Promise<SyncStatus> {
  return request<SyncStatus>("/sync/", { method: "POST" });
}

export function fetchBggCollectionSyncStatus(
  taskId: string,
  signal?: AbortSignal,
): Promise<SyncStatus> {
  return request<SyncStatus>(`/sync/${encodeURIComponent(taskId)}/`, {
    signal,
  });
}
