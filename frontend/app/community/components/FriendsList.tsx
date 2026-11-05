"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

interface Player {
  user_id: string;
  display_name: string;
  avatar?: string | null;
}

interface FriendRequest {
  id: number;
  from_user: Player;
  to_user: Player;
  status: string;
}

interface FriendRequests {
  incoming: FriendRequest[];
  outgoing: FriendRequest[];
}

const DEFAULT_AVATAR = "/avatars/avatar1.webp";

const ALLOWED_AVATARS = new Set([
  "/avatars/brandon.webp",
  "/avatars/sydney.webp",
  "/avatars/jennifer.webp",
  "/avatars/supriya.webp",
  "/avatars/avatar1.webp",
  "/avatars/avatar2.webp",
  "/avatars/avatar3.webp",
  "/avatars/avatar4.webp",
  "/avatars/avatar5.webp",
]);

function getPlayerAvatar(avatar?: string | null): string {
  return avatar && ALLOWED_AVATARS.has(avatar) ? avatar : DEFAULT_AVATAR;
}

function isOptionalAvatar(value: unknown): boolean {
  return value === undefined || value === null || typeof value === "string";
}

function isPlayer(value: unknown): value is Player {
  return (
    typeof value === "object" &&
    value !== null &&
    "user_id" in value &&
    typeof value.user_id === "string" &&
    "display_name" in value &&
    typeof value.display_name === "string" &&
    (!("avatar" in value) || isOptionalAvatar(value.avatar))
  );
}

function isFriendRequest(value: unknown): value is FriendRequest {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    typeof value.id === "number" &&
    "from_user" in value &&
    isPlayer(value.from_user) &&
    "to_user" in value &&
    isPlayer(value.to_user) &&
    "status" in value &&
    typeof value.status === "string"
  );
}

function getCsrfToken(): string | null {
  const cookie = document.cookie
    .split("; ")
    .find(
      (item) => item.startsWith("csrftoken=") || item.startsWith("csrf_token="),
    );

  return cookie
    ? decodeURIComponent(cookie.split("=").slice(1).join("="))
    : null;
}

async function apiRequest(
  url: string,
  method: "POST" | "DELETE",
  body?: object,
): Promise<void> {
  const token = getCsrfToken();

  const response = await fetch(url, {
    method,
    credentials: "same-origin",
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { "X-CSRFToken": token } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  if (response.ok) return;

  if (response.status === 401 || response.status === 403) {
    throw new Error(
      "Please log in again or check your session and CSRF token.",
    );
  }

  if (response.status === 429) {
    throw new Error("Too many requests. Please wait before trying again.");
  }

  if (response.status === 400) {
    throw new Error(
      "Unable to complete this action. Check whether the player is already your friend or has a private profile.",
    );
  }

  if (response.status === 404) {
    throw new Error("This player or request is no longer available.");
  }

  throw new Error("Something went wrong. Please try again.");
}

async function fetchFriends(signal?: AbortSignal): Promise<Player[]> {
  const response = await fetch("/api/v1/friends/", {
    credentials: "same-origin",
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error("Unable to load friends.");
  }

  const data: unknown = await response.json();

  if (!Array.isArray(data) || !data.every(isPlayer)) {
    throw new Error("Unexpected friends response.");
  }

  return data;
}

async function fetchFriendRequests(
  signal?: AbortSignal,
): Promise<FriendRequests> {
  const response = await fetch("/api/v1/friend-requests/", {
    credentials: "same-origin",
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error("Unable to load friend requests.");
  }

  const data: unknown = await response.json();

  if (
    typeof data !== "object" ||
    data === null ||
    !("incoming" in data) ||
    !Array.isArray(data.incoming) ||
    !data.incoming.every(isFriendRequest) ||
    !("outgoing" in data) ||
    !Array.isArray(data.outgoing) ||
    !data.outgoing.every(isFriendRequest)
  ) {
    throw new Error("Unexpected friend requests response.");
  }

  return {
    incoming: data.incoming,
    outgoing: data.outgoing,
  };
}

async function searchPlayers(
  query: string,
  signal: AbortSignal,
): Promise<Player[]> {
  const response = await fetch(
    `/api/v1/players/?search=${encodeURIComponent(query)}`,
    {
      credentials: "same-origin",
      cache: "no-store",
      signal,
    },
  );

  if (!response.ok) {
    throw new Error("Unable to search registered players.");
  }

  const data: unknown = await response.json();

  if (!Array.isArray(data) || !data.every(isPlayer)) {
    throw new Error("Unexpected player search response.");
  }

  return data;
}

interface RequestRowProps {
  name: string;
  busy: boolean;
  actions: {
    label: string;
    onClick: () => void;
    destructive?: boolean;
  }[];
}

function RequestRow({ name, busy, actions }: RequestRowProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-700 bg-slate-800/50 p-3">
      <span className="font-medium">{name}</span>

      <div className="flex flex-wrap gap-2">
        {actions.map((action) => (
          <button
            key={action.label}
            type="button"
            disabled={busy}
            onClick={action.onClick}
            className={`rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50 ${
              action.destructive
                ? "bg-slate-700 text-red-300 hover:bg-slate-600"
                : "bg-indigo-600 text-white hover:bg-indigo-500"
            }`}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// TODO: Extract search, friends, and request panels into smaller components.
// eslint-disable-next-line complexity
export default function FriendsList() {
  const [friends, setFriends] = useState<Player[]>([]);
  const [requests, setRequests] = useState<FriendRequests>({
    incoming: [],
    outgoing: [],
  });

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [searchError, setSearchError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const [friendData, requestData] = await Promise.all([
          fetchFriends(controller.signal),
          fetchFriendRequests(controller.signal),
        ]);

        if (!controller.signal.aborted) {
          setFriends(friendData);
          setRequests(requestData);
        }
      } catch (caughtError) {
        if (!controller.signal.aborted) {
          setError(
            caughtError instanceof Error
              ? caughtError.message
              : "Unable to load friends.",
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => controller.abort();
  }, []);

  useEffect(() => {
    const search = query.trim();

    if (search.length < 2 || search.length > 100) {
      return;
    }

    const controller = new AbortController();

    const timeout = setTimeout(async () => {
      setSearchLoading(true);
      setSearchError("");

      try {
        const players = await searchPlayers(search, controller.signal);

        if (!controller.signal.aborted) {
          setResults(players);
        }
      } catch (caughtError) {
        if (!controller.signal.aborted) {
          setResults([]);
          setSearchError(
            caughtError instanceof Error
              ? caughtError.message
              : "Unable to search players.",
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setSearchLoading(false);
        }
      }
    }, 350);

    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [query]);

  async function refreshFriends() {
    const [friendData, requestData] = await Promise.all([
      fetchFriends(),
      fetchFriendRequests(),
    ]);

    setFriends(friendData);
    setRequests(requestData);
  }

  async function performAction(
    url: string,
    method: "POST" | "DELETE",
    successMessage: string,
    body?: object,
  ) {
    if (busy) return;

    setBusy(true);
    setError("");
    setMessage("");

    try {
      await apiRequest(url, method, body);
      await refreshFriends();
      setMessage(successMessage);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to complete action.",
      );
    } finally {
      setBusy(false);
    }
  }

  const friendIds = new Set(friends.map((friend) => friend.user_id));

  const pendingIds = new Set(
    requests.outgoing.map((request) => request.to_user.user_id),
  );

  const incomingIds = new Set(
    requests.incoming.map((request) => request.from_user.user_id),
  );

  return (
    <section className="border-t border-gray-500 pt-6">
      <h2 className="mb-6 text-3xl font-bold tracking-wide">YOUR FRIENDS</h2>

      {error && (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-red-700 bg-red-950 p-3 text-sm text-red-300"
        >
          {error}
        </p>
      )}

      {message && (
        <p
          role="status"
          className="mb-4 rounded-lg border border-emerald-700 bg-emerald-950 p-3 text-sm text-emerald-300"
        >
          {message}
        </p>
      )}

      <div className="mb-6 space-y-3">
        <label className="block text-sm font-medium text-slate-200">
          Find QuestLog Players
          <input
            type="search"
            value={query}
            maxLength={100}
            onChange={(event) => {
              setQuery(event.target.value);
              setResults([]);
              setSearchError("");
              setSearchLoading(false);
            }}
            placeholder="Search by display name..."
            className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 p-3 text-white"
          />
        </label>

        {query.trim().length === 1 && (
          <p className="text-xs text-slate-400">
            Enter at least 2 characters to search.
          </p>
        )}

        {searchLoading && (
          <p role="status" className="text-sm text-slate-400">
            Searching players...
          </p>
        )}

        {searchError && (
          <p role="alert" className="text-sm text-red-400">
            {searchError}
          </p>
        )}

        {query.trim().length >= 2 &&
          !searchLoading &&
          !searchError &&
          results.length === 0 && (
            <p className="text-sm text-slate-400">No matching players found.</p>
          )}

        {results
          .filter((player) => !friendIds.has(player.user_id))
          .map((player) => {
            const pending = pendingIds.has(player.user_id);
            const incoming = incomingIds.has(player.user_id);

            return (
              <RequestRow
                key={player.user_id}
                name={player.display_name}
                busy={busy}
                actions={[
                  {
                    label: pending
                      ? "Request Sent"
                      : incoming
                        ? "Request Received"
                        : "Add Friend",
                    onClick: () => {
                      if (pending || incoming) return;

                      void performAction(
                        "/api/v1/friend-requests/",
                        "POST",
                        `Friend request sent to ${player.display_name}.`,
                        { user_id: player.user_id },
                      );
                    },
                  },
                ]}
              />
            );
          })}
      </div>

      <div className="space-y-4">
        {loading && <p className="text-gray-400">Loading your friends...</p>}

        {!loading && friends.length === 0 && (
          <div className="rounded-xl border border-gray-700 bg-slate-800/40 p-5">
            <p className="text-lg font-medium">No friends yet</p>
            <p className="mt-2 text-sm text-gray-400">
              Search for registered players above to start connecting.
            </p>
          </div>
        )}

        {!loading && friends.length > 0 && (
          <ul className="space-y-4">
            {friends.map((friend) => (
              <li
                key={friend.user_id}
                className="flex items-center justify-between gap-3"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <Image
                    src={getPlayerAvatar(friend.avatar)}
                    alt=""
                    width={48}
                    height={48}
                    className="h-12 w-12 rounded-full border border-gray-500 object-cover"
                  />
                  <span className="truncate font-medium">
                    {friend.display_name}
                  </span>
                </div>

                <button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    void performAction(
                      `/api/v1/friends/${friend.user_id}/`,
                      "DELETE",
                      `${friend.display_name} was removed from your friends.`,
                    )
                  }
                  className="rounded-lg border border-slate-600 px-3 py-2 text-xs text-red-300 hover:bg-slate-800 disabled:opacity-50"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-8 space-y-4 border-t border-slate-700 pt-6">
        <h3 className="text-xl font-semibold">Friend Requests</h3>

        <div className="space-y-3">
          <h4 className="font-medium text-slate-200">Incoming</h4>

          {!loading && requests.incoming.length === 0 && (
            <p className="text-sm text-slate-400">No incoming requests.</p>
          )}

          {requests.incoming.map((request) => (
            <RequestRow
              key={request.id}
              name={request.from_user.display_name}
              busy={busy}
              actions={[
                {
                  label: "Accept",
                  onClick: () =>
                    void performAction(
                      `/api/v1/friend-requests/${request.id}/accept/`,
                      "POST",
                      `You are now friends with ${request.from_user.display_name}.`,
                    ),
                },
                {
                  label: "Decline",
                  destructive: true,
                  onClick: () =>
                    void performAction(
                      `/api/v1/friend-requests/${request.id}/decline/`,
                      "POST",
                      "Friend request declined.",
                    ),
                },
              ]}
            />
          ))}
        </div>

        <div className="space-y-3">
          <h4 className="font-medium text-slate-200">Sent</h4>

          {!loading && requests.outgoing.length === 0 && (
            <p className="text-sm text-slate-400">No pending sent requests.</p>
          )}

          {requests.outgoing.map((request) => (
            <RequestRow
              key={request.id}
              name={request.to_user.display_name}
              busy={busy}
              actions={[
                {
                  label: "Cancel Request",
                  destructive: true,
                  onClick: () =>
                    void performAction(
                      `/api/v1/friend-requests/${request.id}/`,
                      "DELETE",
                      "Friend request canceled.",
                    ),
                },
              ]}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
