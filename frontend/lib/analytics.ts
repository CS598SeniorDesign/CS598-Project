/**
 * Client for the head-to-head, group statistics and relationship tag
 * endpoints (/api/v1/analytics/...).
 *
 * Head-to-head and tags are always from the signed-in user's point of view:
 * "you" is the user, "they" is the other player. Tags are private to the user
 * who holds them.
 */

import { apiRequest, toQueryString } from "@/lib/api";

export interface PlayerReference {
  user_id: string;
  display_name: string;
}

export interface HeadToHeadGame {
  bgg_id: number;
  name: string;
  sessions: number;
  you_won: number;
  they_won: number;
}

/**
 * The user's record against one player. you_won, they_won, both_won and
 * neither_won count completed games and add up to completed_sessions.
 */
export interface HeadToHead {
  opponent: PlayerReference;
  sessions_together: number;
  plays_together: number;
  completed_sessions: number;
  you_won: number;
  they_won: number;
  both_won: number;
  neither_won: number;
  your_win_rate: number | null;
  their_win_rate: number | null;
  last_played: string | null;
  games: HeadToHeadGame[];
}

export interface GroupGame {
  bgg_id: number;
  name: string;
  sessions: number;
  plays: number;
}

export interface GroupStanding {
  player: PlayerReference;
  sessions: number;
  wins: number;
  win_rate: number | null;
}

export interface GroupMonth {
  month: string;
  sessions: number;
  plays: number;
}

export interface GroupStatistics {
  group_id: number;
  group_name: string;
  member_count: number;
  total_sessions: number;
  total_plays: number;
  total_play_time_minutes: number;
  last_played: string | null;
  most_played_games: GroupGame[];
  leaderboard: GroupStanding[];
  monthly_activity: GroupMonth[];
}

export const RELATIONSHIP_TAG_TYPES = [
  "MORTAL_ENEMY",
  "PUNCHING_BAG",
  "RIVAL",
  "SIDEKICK",
  "DOOMED_DUO",
  "REGULAR",
  "LUCKY_CHARM",
  "JINX",
  "LONG_TIME_NO_SEE",
] as const;

export type RelationshipTagType = (typeof RELATIONSHIP_TAG_TYPES)[number];

export interface RelationshipTag {
  tag_type: RelationshipTagType;
  name: string;
  description: string;
  assigned_at: string;
}

export interface FriendTags {
  friend: PlayerReference;
  tags: RelationshipTag[];
}

const BASE_URL = "/api/v1/analytics";

function describeStatisticsError(
  notFoundMessage: string,
): (status: number) => string {
  return (status) => {
    if (status === 401 || status === 403) {
      return "Please log in to view statistics.";
    }
    if (status === 404) return notFoundMessage;
    return "Unable to load statistics. Please try again.";
  };
}

/** The signed-in user's record against another player. */
export function fetchHeadToHead(
  userId: string,
  signal?: AbortSignal,
): Promise<HeadToHead> {
  return apiRequest<HeadToHead>(
    `${BASE_URL}/head-to-head/${encodeURIComponent(userId)}/`,
    { signal },
    describeStatisticsError("No statistics are available for this player."),
  );
}

/** Statistics for one of the signed-in user's game groups. */
export function fetchGroupStatistics(
  groupId: number,
  signal?: AbortSignal,
): Promise<GroupStatistics> {
  return apiRequest<GroupStatistics>(
    `${BASE_URL}/groups/${groupId}/`,
    { signal },
    describeStatisticsError("Statistics for this group are not available."),
  );
}

/**
 * The relationship tags the signed-in user holds about their friends, grouped
 * by friend. Pass a user ID to get only that friend's tags.
 */
export function fetchRelationshipTags(
  options: { userId?: string; signal?: AbortSignal } = {},
): Promise<FriendTags[]> {
  return apiRequest<FriendTags[]>(
    `${BASE_URL}/tags/${toQueryString({ user_id: options.userId })}`,
    { signal: options.signal },
    describeStatisticsError("No tags are available."),
  );
}

/** Index friends' tags by user ID. */
export function tagsByFriend(
  entries: FriendTags[],
): Record<string, RelationshipTag[]> {
  return Object.fromEntries(
    entries.map((entry) => [entry.friend.user_id, entry.tags]),
  );
}

/** Format a win rate from the API, e.g. 66.7 -> "66.7%", null -> "N/A". */
export function formatWinRate(value: number | null): string {
  return value === null ? "N/A" : `${value.toFixed(1)}%`;
}

/**
 * Format a play date from the API (YYYY-MM-DD) in the user's locale, e.g.
 * "Nov 20, 2026". The date is read as local time so it never shifts a day.
 */
export function formatPlayDate(value: string): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Format a length of time in minutes, e.g. 135 -> "2h 15m", 45 -> "45m". */
export function formatPlayTime(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;

  if (hours === 0) return `${remaining}m`;
  return remaining === 0 ? `${hours}h` : `${hours}h ${remaining}m`;
}
