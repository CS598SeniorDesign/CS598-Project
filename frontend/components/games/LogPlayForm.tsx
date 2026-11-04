"use client";

import { useEffect, useState, type FormEvent } from "react";

interface LogPlayFormProps {
  gameId: number;
  gameName: string;
  onClose: () => void;
}

type PlayerType = "guest" | "registered";
type PlayerSource = "friends" | "search";

interface RegisteredPlayer {
  user_id: string;
  display_name: string;
}

interface PlayerInput {
  id: number;
  type: PlayerType;
  source: PlayerSource;
  guestName: string;
  userId: string;
  displayName: string;
  score: string;
  isWinner: boolean;
}

function createPlayer(id: number): PlayerInput {
  return {
    id,
    type: "guest",
    source: "friends",
    guestName: "",
    userId: "",
    displayName: "",
    score: "",
    isWinner: false,
  };
}

function getCookie(name: string): string | null {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));

  return cookie
    ? decodeURIComponent(cookie.split("=").slice(1).join("="))
    : null;
}

function getCsrfToken(): string | null {
  return getCookie("csrftoken") ?? getCookie("csrf_token");
}

function getLocalDate(): string {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function validatePlayers(players: PlayerInput[]): string | null {
  const guests = players.filter((player) => player.type === "guest");
  const registered = players.filter((player) => player.type === "registered");

  const guestNames = guests.map((player) => player.guestName.trim());

  if (guestNames.some((name) => !name)) {
    return "Please enter a name for every guest player.";
  }

  if (
    new Set(guestNames.map((name) => name.toLowerCase())).size !==
    guestNames.length
  ) {
    return "Each guest player must have a different name.";
  }

  const userIds = registered.map((player) => player.userId);

  if (userIds.some((id) => !id)) {
    return "Please select a registered QuestLog user for every registered player.";
  }

  if (new Set(userIds).size !== userIds.length) {
    return "The same registered user cannot be added twice.";
  }

  if (
    players.some(
      (player) =>
        player.score.trim() !== "" && !Number.isFinite(Number(player.score)),
    )
  ) {
    return "Please enter a valid score for each player.";
  }

  return null;
}

function validatePlayDetails(
  duration: string,
  players: PlayerInput[],
): string | null {
  if (
    duration &&
    (!Number.isInteger(Number(duration)) || Number(duration) <= 0)
  ) {
    return "Duration must be a positive whole number.";
  }

  return validatePlayers(players);
}

function buildPlayPayload(
  gameId: number,
  playDate: string,
  duration: string,
  notes: string,
  players: PlayerInput[],
) {
  return {
    game: gameId,
    play_date: playDate,
    quantity: 1,
    is_incomplete: false,
    ...(duration ? { play_time_minutes: Number(duration) } : {}),
    ...(notes.trim() ? { notes: notes.trim() } : {}),
    players: players.map((player) => ({
      ...(player.type === "registered"
        ? { user_id: player.userId }
        : { guest_name: player.guestName.trim() }),
      ...(player.score.trim() !== "" ? { score: Number(player.score) } : {}),
      is_winner: player.isWinner,
    })),
  };
}

async function fetchRegisteredPlayers(
  url: string,
  signal?: AbortSignal,
): Promise<RegisteredPlayer[]> {
  const response = await fetch(url, {
    credentials: "same-origin",
    signal,
  });

  if (!response.ok) {
    throw new Error(
      response.status === 401 || response.status === 403
        ? "Please log in to find registered players."
        : "Unable to load registered players. Please try again.",
    );
  }

  const data: unknown = await response.json();

  if (
    !Array.isArray(data) ||
    !data.every(
      (item: unknown) =>
        typeof item === "object" &&
        item !== null &&
        "user_id" in item &&
        typeof item.user_id === "string" &&
        "display_name" in item &&
        typeof item.display_name === "string",
    )
  ) {
    throw new Error("Unexpected player list response.");
  }

  return data as RegisteredPlayer[];
}

async function savePlaySession(
  payload: ReturnType<typeof buildPlayPayload>,
): Promise<void> {
  const csrfToken = getCsrfToken();

  const response = await fetch("/api/v1/plays/", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (response.ok) return;

  if (response.status === 401 || response.status === 403) {
    throw new Error(
      "Please log in again. If you're already logged in, check your session and CSRF token.",
    );
  }

  if (response.status === 400) {
    throw new Error(
      "Unable to save this play. Check the player details, account permissions, and game catalog.",
    );
  }

  throw new Error("Unable to save your play. Please try again.");
}

function usePlayerDirectory(source: PlayerSource, query: string) {
  const [players, setPlayers] = useState<RegisteredPlayer[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const search = query.trim();
    const isFriends = source === "friends";
    const validSearch = search.length >= 2 && search.length <= 100;

    if (!isFriends && !validSearch) {
      return;
    }

    const controller = new AbortController();
    let active = true;

    const url = isFriends
      ? "/api/v1/friends/"
      : `/api/v1/players/?search=${encodeURIComponent(search)}`;

    const delay = isFriends ? 0 : 350;

    const timeout = setTimeout(() => {
      async function loadPlayers() {
        setLoading(true);
        setError("");

        try {
          const data = await fetchRegisteredPlayers(url, controller.signal);

          if (active) setPlayers(data);
        } catch (caughtError) {
          if (active) {
            setError(
              caughtError instanceof Error
                ? caughtError.message
                : "Unable to load players.",
            );
          }
        } finally {
          if (active) setLoading(false);
        }
      }

      void loadPlayers();
    }, delay);

    return () => {
      active = false;
      clearTimeout(timeout);
      controller.abort();
    };
  }, [source, query]);

  return { players, loading, error };
}

interface PlayerSelectProps {
  player: PlayerInput;
  candidates: RegisteredPlayer[];
  selectedUserIds: string[];
  onSelect: (user: RegisteredPlayer) => void;
}

function PlayerSelect({
  player,
  candidates,
  selectedUserIds,
  onSelect,
}: PlayerSelectProps) {
  const availablePlayers = candidates.filter(
    (candidate) =>
      candidate.user_id === player.userId ||
      !selectedUserIds.includes(candidate.user_id),
  );

  const selectedIsMissing =
    Boolean(player.userId) &&
    !availablePlayers.some((candidate) => candidate.user_id === player.userId);

  return (
    <label className="block text-sm text-slate-200">
      Select Registered User
      <select
        value={player.userId}
        onChange={(event) => {
          const selected = availablePlayers.find(
            (candidate) => candidate.user_id === event.target.value,
          );

          if (selected) onSelect(selected);
        }}
        className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 p-3 text-white"
      >
        <option value="">Choose a player</option>

        {availablePlayers.map((candidate) => (
          <option key={candidate.user_id} value={candidate.user_id}>
            {candidate.display_name}
          </option>
        ))}

        {selectedIsMissing && (
          <option value={player.userId}>{player.displayName}</option>
        )}
      </select>
    </label>
  );
}

interface PlayerPickerResultsProps {
  player: PlayerInput;
  candidates: RegisteredPlayer[];
  selectedUserIds: string[];
  loading: boolean;
  error: string;
  showResults: boolean;
  onSelect: (user: RegisteredPlayer) => void;
}

function PlayerPickerResults({
  player,
  candidates,
  selectedUserIds,
  loading,
  error,
  showResults,
  onSelect,
}: PlayerPickerResultsProps) {
  if (!showResults) return null;

  if (loading) {
    return (
      <p role="status" className="text-sm text-slate-400">
        Loading players...
      </p>
    );
  }

  if (error) {
    return (
      <p role="alert" className="text-sm text-red-400">
        {error}
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <PlayerSelect
        player={player}
        candidates={candidates}
        selectedUserIds={selectedUserIds}
        onSelect={onSelect}
      />

      {candidates.length === 0 && (
        <p className="text-xs text-slate-400">
          {player.source === "friends"
            ? "No addable friends found. Try searching for a user."
            : "No matching registered users found."}
        </p>
      )}
    </div>
  );
}

interface RegisteredPlayerPickerProps {
  player: PlayerInput;
  selectedUserIds: string[];
  onSourceChange: (source: PlayerSource) => void;
  onSelect: (user: RegisteredPlayer) => void;
}

function RegisteredPlayerPicker({
  player,
  selectedUserIds,
  onSourceChange,
  onSelect,
}: RegisteredPlayerPickerProps) {
  const [query, setQuery] = useState("");
  const { players, loading, error } = usePlayerDirectory(player.source, query);

  const showResults =
    player.source === "friends" ||
    (query.trim().length >= 2 && query.trim().length <= 100);

  function changeSource(source: PlayerSource) {
    setQuery("");
    onSourceChange(source);
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => changeSource("friends")}
          aria-pressed={player.source === "friends"}
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            player.source === "friends"
              ? "bg-indigo-600 text-white"
              : "bg-slate-700 text-slate-200 hover:bg-slate-600"
          }`}
        >
          My Friends
        </button>

        <button
          type="button"
          onClick={() => changeSource("search")}
          aria-pressed={player.source === "search"}
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            player.source === "search"
              ? "bg-indigo-600 text-white"
              : "bg-slate-700 text-slate-200 hover:bg-slate-600"
          }`}
        >
          Search Users
        </button>
      </div>

      {player.source === "search" && (
        <label className="block text-sm text-slate-200">
          Search by Display Name
          <input
            type="text"
            maxLength={100}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Enter at least 2 characters"
            className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 p-3 text-white"
          />
        </label>
      )}

      {player.source === "search" && query.trim().length < 2 && (
        <p className="text-xs text-slate-400">
          Enter at least 2 characters to find registered users.
        </p>
      )}

      <PlayerPickerResults
        player={player}
        candidates={players}
        selectedUserIds={selectedUserIds}
        loading={loading}
        error={error}
        showResults={showResults}
        onSelect={onSelect}
      />

      {player.userId && (
        <p className="text-sm text-emerald-300">
          Selected: {player.displayName}
        </p>
      )}
    </div>
  );
}

interface PlayerCardProps {
  player: PlayerInput;
  index: number;
  canRemove: boolean;
  selectedUserIds: string[];
  onRemove: () => void;
  onUpdate: (changes: Partial<PlayerInput>) => void;
  onTypeChange: (type: PlayerType) => void;
  onSourceChange: (source: PlayerSource) => void;
}

function PlayerCard({
  player,
  index,
  canRemove,
  selectedUserIds,
  onRemove,
  onUpdate,
  onTypeChange,
  onSourceChange,
}: PlayerCardProps) {
  return (
    <div className="space-y-3 rounded-xl border border-slate-700 bg-slate-800 p-4">
      <div className="flex items-center justify-between">
        <span className="font-medium">Player {index + 1}</span>

        {canRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="text-sm text-red-400 hover:text-red-300"
          >
            Remove
          </button>
        )}
      </div>

      <label className="block text-sm text-slate-200">
        Player Type
        <select
          value={player.type}
          onChange={(event) => onTypeChange(event.target.value as PlayerType)}
          className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 p-3 text-white"
        >
          <option value="guest">Guest Player</option>
          <option value="registered">Registered QuestLog User</option>
        </select>
      </label>

      {player.type === "guest" ? (
        <label className="block text-sm text-slate-200">
          Guest Name
          <input
            type="text"
            required
            value={player.guestName}
            onChange={(event) => onUpdate({ guestName: event.target.value })}
            placeholder="Enter player name"
            className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 p-3 text-white"
          />
        </label>
      ) : (
        <RegisteredPlayerPicker
          player={player}
          selectedUserIds={selectedUserIds}
          onSourceChange={onSourceChange}
          onSelect={(user) =>
            onUpdate({
              userId: user.user_id,
              displayName: user.display_name,
            })
          }
        />
      )}

      <div className="flex items-end gap-4">
        <label className="block flex-1 text-sm text-slate-200">
          Score (optional)
          <input
            type="number"
            step="any"
            value={player.score}
            onChange={(event) => onUpdate({ score: event.target.value })}
            placeholder="Score"
            className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 p-3 text-white"
          />
        </label>

        <label className="flex items-center gap-2 pb-3 text-sm text-slate-200">
          <input
            type="checkbox"
            checked={player.isWinner}
            onChange={(event) => onUpdate({ isWinner: event.target.checked })}
            className="h-4 w-4 accent-indigo-600"
          />
          Winner
        </label>
      </div>
    </div>
  );
}

export default function LogPlayForm({
  gameId,
  gameName,
  onClose,
}: LogPlayFormProps) {
  const [playDate, setPlayDate] = useState(getLocalDate);
  const [duration, setDuration] = useState("");
  const [notes, setNotes] = useState("");
  const [players, setPlayers] = useState<PlayerInput[]>([createPlayer(1)]);
  const [nextPlayerId, setNextPlayerId] = useState(2);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape" && !isSubmitting) {
        onClose();
      }
    }

    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("keydown", handleEscape);
    };
  }, [onClose, isSubmitting]);

  function updatePlayer(id: number, changes: Partial<PlayerInput>) {
    setPlayers((current) =>
      current.map((player) =>
        player.id === id ? { ...player, ...changes } : player,
      ),
    );
  }

  function changePlayerType(id: number, type: PlayerType) {
    updatePlayer(id, {
      type,
      source: "friends",
      guestName: "",
      userId: "",
      displayName: "",
    });
  }

  function changePlayerSource(id: number, source: PlayerSource) {
    updatePlayer(id, {
      source,
      userId: "",
      displayName: "",
    });
  }

  function addPlayer() {
    setPlayers((current) => [...current, createPlayer(nextPlayerId)]);

    setNextPlayerId((current) => current + 1);
  }

  function removePlayer(id: number) {
    setPlayers((current) => current.filter((player) => player.id !== id));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const validationError = validatePlayDetails(duration, players);

    if (validationError) {
      setError(validationError);
      return;
    }

    const payload = buildPlayPayload(
      gameId,
      playDate,
      duration,
      notes,
      players,
    );

    setIsSubmitting(true);

    try {
      await savePlaySession(payload);
      setSuccess(true);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Something went wrong. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const selectedUserIds = players
    .filter((player) => player.type === "registered")
    .map((player) => player.userId)
    .filter(Boolean);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="log-play-title"
        className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 text-white shadow-2xl"
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 id="log-play-title" className="text-2xl font-bold">
              Log a Play
            </h2>
            <p className="mt-1 text-sm text-slate-400">{gameName}</p>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            aria-label="Close Log Play"
            className="rounded-lg px-2 py-1 text-xl text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-50"
          >
            ×
          </button>
        </div>

        {success ? (
          <div role="status" className="space-y-5">
            <p className="rounded-lg border border-emerald-700 bg-emerald-950 p-4 text-emerald-300">
              Your play session was saved successfully!
            </p>
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl bg-indigo-600 px-6 py-3 font-semibold hover:bg-indigo-500"
            >
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-medium text-slate-200">
                Play Date
                <input
                  type="date"
                  required
                  max={getLocalDate()}
                  value={playDate}
                  onChange={(event) => setPlayDate(event.target.value)}
                  className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-800 p-3 text-white"
                />
              </label>

              <label className="block text-sm font-medium text-slate-200">
                Duration (minutes)
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={duration}
                  onChange={(event) => setDuration(event.target.value)}
                  placeholder="Optional"
                  className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-800 p-3 text-white"
                />
              </label>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-semibold">Players</h3>

              {players.map((player, index) => (
                <PlayerCard
                  key={player.id}
                  player={player}
                  index={index}
                  canRemove={players.length > 1}
                  selectedUserIds={selectedUserIds}
                  onRemove={() => removePlayer(player.id)}
                  onUpdate={(changes) => updatePlayer(player.id, changes)}
                  onTypeChange={(type) => changePlayerType(player.id, type)}
                  onSourceChange={(source) =>
                    changePlayerSource(player.id, source)
                  }
                />
              ))}

              <button
                type="button"
                onClick={addPlayer}
                className="text-sm font-semibold text-indigo-300 hover:text-indigo-200"
              >
                + Add Another Player
              </button>
            </div>

            <label className="block text-sm font-medium text-slate-200">
              Notes (optional)
              <textarea
                rows={3}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="How was game night?"
                className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-800 p-3 text-white"
              />
            </label>

            {error && (
              <p
                role="alert"
                className="rounded-lg border border-red-700 bg-red-950 p-3 text-sm text-red-300"
              >
                {error}
              </p>
            )}

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="rounded-xl border border-slate-600 px-5 py-3 font-semibold hover:bg-slate-800 disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={isSubmitting}
                className="rounded-xl bg-indigo-600 px-6 py-3 font-semibold hover:bg-indigo-500 disabled:opacity-50"
              >
                {isSubmitting ? "Saving..." : "Save Play"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
