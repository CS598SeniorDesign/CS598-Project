"use client";

import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  CalendarDays,
  Check,
  Clock3,
  Dice5,
  Gamepad2,
  LoaderCircle,
  MapPin,
  Pencil,
  Plus,
  Sparkles,
  Trash2,
  Users,
  X,
} from "lucide-react";
import ShowMoreButton from "./ShowMoreButton";

type RSVPStatus = "GOING" | "MAYBE" | "NOT_GOING";
type EventGame = {
  bgg_id: number;
  primary_name: string;
  thumbnail_url?: string | null;
};
type EventGroup = { id: number; name: string };
type EventHost = { user_id: string; display_name: string };
type GameEvent = {
  id: number;
  title: string;
  description: string;
  starts_at: string;
  location: string;
  game: EventGame | null;
  group: EventGroup | null;
  host: EventHost | null;
  is_host: boolean;
  going_count: number;
  my_rsvp: RSVPStatus | null;
};
type GroupOption = { id: number; name: string };
type GameOption = { bgg_id: number; primary_name: string };
type EventForm = {
  title: string;
  starts_at: string;
  location: string;
  description: string;
  group_id: string;
  game_id: string;
};
const INITIAL_VISIBLE = 4;
const EMPTY_FORM: EventForm = {
  title: "",
  starts_at: "",
  location: "",
  description: "",
  group_id: "",
  game_id: "",
};
const RSVP_OPTIONS: { value: RSVPStatus; label: string }[] = [
  { value: "GOING", label: "Going" },
  { value: "MAYBE", label: "Maybe" },
  { value: "NOT_GOING", label: "Can't Go" },
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
function isGameEvent(value: unknown): value is GameEvent {
  return (
    isRecord(value) &&
    typeof value.id === "number" &&
    typeof value.title === "string" &&
    typeof value.starts_at === "string" &&
    typeof value.is_host === "boolean" &&
    typeof value.going_count === "number"
  );
}
function isGroup(value: unknown): value is GroupOption {
  return (
    isRecord(value) &&
    typeof value.id === "number" &&
    typeof value.name === "string"
  );
}
function isGame(value: unknown): value is GameOption {
  return (
    isRecord(value) &&
    typeof value.bgg_id === "number" &&
    typeof value.primary_name === "string"
  );
}
function getCookie(name: string): string | null {
  const item = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${name}=`));
  return item ? decodeURIComponent(item.slice(name.length + 1)) : null;
}
function csrf(): string {
  return getCookie("csrftoken") ?? getCookie("csrf_token") ?? "";
}
function message(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}
async function api(url: string, options: RequestInit = {}): Promise<unknown> {
  const response = await fetch(url, {
    credentials: "same-origin",
    cache: "no-store",
    ...options,
  });
  if (!response.ok) {
    let detail = "";
    try {
      const body: unknown = await response.json();
      if (isRecord(body)) detail = String(body.detail ?? body.error ?? "");
    } catch {
      /* Non-JSON error response */
    }
    throw new Error(
      detail || `Request failed (${response.status}). Please try again.`,
    );
  }
  if (response.status === 204) return null;
  const text = await response.text();
  return text ? (JSON.parse(text) as unknown) : null;
}
async function write(
  url: string,
  method: "POST" | "PATCH" | "DELETE",
  body?: Record<string, unknown>,
) {
  await api(url, {
    method,
    headers: {
      "X-CSRFToken": csrf(),
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
}
async function fetchEvents(signal?: AbortSignal): Promise<GameEvent[]> {
  const data = await api("/api/v1/events/", { signal });
  if (!Array.isArray(data)) throw new Error("Unexpected events response.");
  const now = Date.now();
  return data
    .filter(isGameEvent)
    .filter((event) => Date.parse(event.starts_at) >= now)
    .sort((a, b) => Date.parse(a.starts_at) - Date.parse(b.starts_at));
}
async function fetchGroups(): Promise<GroupOption[]> {
  const data = await api("/api/v1/groups/");
  if (!Array.isArray(data)) throw new Error("Unexpected groups response.");
  return data.filter(isGroup);
}
const GAME_SEARCH_URL = "/api/v1/games/";
async function searchGames(term: string): Promise<GameOption[]> {
  const data = await api(
    `${GAME_SEARCH_URL}?search=${encodeURIComponent(term)}`,
  );
  const rows: unknown =
    isRecord(data) && Array.isArray(data.results) ? data.results : data;
  if (!Array.isArray(rows))
    throw new Error("Unexpected game catalog response.");
  return rows.filter(isGame).slice(0, 12);
}
function localDateTime(iso: string): string {
  const date = new Date(iso);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}
function formFromEvent(event?: GameEvent): EventForm {
  if (!event) return { ...EMPTY_FORM };
  return {
    title: event.title,
    starts_at: localDateTime(event.starts_at),
    location: event.location ?? "",
    description: event.description ?? "",
    group_id: event.group ? String(event.group.id) : "",
    game_id: event.game ? String(event.game.bgg_id) : "",
  };
}
function payloadFromForm(form: EventForm): Record<string, unknown> {
  const date = new Date(form.starts_at);
  if (Number.isNaN(date.getTime()) || date.getTime() <= Date.now()) {
    throw new Error("Please select a future date and time.");
  }
  return {
    title: form.title.trim(),
    starts_at: date.toISOString(),
    location: form.location.trim(),
    description: form.description.trim(),
    group_id: form.group_id ? Number(form.group_id) : null,
    game_id: form.game_id ? Number(form.game_id) : null,
  };
}
function dateLabel(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}
function timeLabel(value: string): string {
  return new Date(value).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}
function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/75 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 text-slate-100 shadow-2xl"
      >
        <div className="mb-5 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-xl font-bold">{title}</h3>
            <p className="mt-1 text-sm text-slate-400">
              Plan something fun with your community.
            </p>
          </div>
          <button
            type="button"
            aria-label="Close dialog"
            onClick={onClose}
            className="rounded-lg p-2 hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
const FIELD_CLASS =
  "w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-400";
function TextField({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  placeholder = "",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <label className="block space-y-1.5 text-sm font-medium text-slate-200">
      <span>{label}</span>
      <input
        type={type}
        required={required}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={FIELD_CLASS}
      />
    </label>
  );
}
function GameSelector({
  value,
  onChange,
  current,
}: {
  value: string;
  onChange: (value: string) => void;
  current?: EventGame | null;
}) {
  const [query, setQuery] = useState(current?.primary_name ?? "");
  const [results, setResults] = useState<GameOption[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function runSearch() {
    setLoading(true);
    setError("");
    try {
      setResults(await searchGames(query.trim()));
    } catch (err) {
      setError(`Game search unavailable: ${message(err)}`);
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-slate-200">
        Board Game (optional)
      </label>
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for Catan, Azul..."
          className={FIELD_CLASS}
        />
        <button
          type="button"
          disabled={loading || !query.trim()}
          onClick={() => void runSearch()}
          className="rounded-lg bg-slate-700 px-3 text-xs font-semibold hover:bg-slate-600 disabled:opacity-50"
        >
          Search
        </button>
      </div>
      {value && (
        <div className="flex items-center justify-between rounded-lg bg-indigo-500/15 px-3 py-2 text-xs text-indigo-200">
          <span>Selected game: {query || `BGG #${value}`}</span>
          <button
            type="button"
            onClick={() => {
              onChange("");
              setQuery("");
              setResults([]);
            }}
          >
            Clear
          </button>
        </div>
      )}
      {results.length > 0 && (
        <div className="max-h-36 overflow-y-auto rounded-lg border border-slate-700">
          {results.map((game) => (
            <button
              key={game.bgg_id}
              type="button"
              onClick={() => {
                onChange(String(game.bgg_id));
                setQuery(game.primary_name);
                setResults([]);
              }}
              className="block w-full border-b border-slate-700 px-3 py-2 text-left text-sm hover:bg-slate-800"
            >
              {game.primary_name}
            </button>
          ))}
        </div>
      )}
      {error && <p className="text-xs text-amber-300">{error}</p>}
      <p className="text-xs text-slate-500">
        Select a search result to attach a game to the event.
      </p>
    </div>
  );
}
function EventFormFields({
  form,
  setForm,
  groups,
  original,
}: {
  form: EventForm;
  setForm: (form: EventForm) => void;
  groups: GroupOption[];
  original?: GameEvent;
}) {
  function change(field: keyof EventForm, value: string) {
    setForm({ ...form, [field]: value });
  }
  return (
    <div className="space-y-4">
      <TextField
        label="Event Name"
        value={form.title}
        required
        placeholder="Friday Board Game Night"
        onChange={(v) => change("title", v)}
      />
      <TextField
        label="Date & Time"
        type="datetime-local"
        value={form.starts_at}
        required
        onChange={(v) => change("starts_at", v)}
      />
      <TextField
        label="Location"
        value={form.location}
        placeholder="RSC 231"
        onChange={(v) => change("location", v)}
      />
      <label className="block space-y-1.5 text-sm font-medium text-slate-200">
        <span>Description</span>
        <textarea
          rows={3}
          value={form.description}
          onChange={(e) => change("description", e.target.value)}
          placeholder="Tell everyone what to expect..."
          className={FIELD_CLASS}
        />
      </label>
      <label className="block space-y-1.5 text-sm font-medium text-slate-200">
        <span>Game Group (optional)</span>
        <select
          value={form.group_id}
          onChange={(e) => change("group_id", e.target.value)}
          className={FIELD_CLASS}
        >
          <option value="">No group / open community event</option>
          {groups.map((group) => (
            <option key={group.id} value={group.id}>
              {group.name}
            </option>
          ))}
        </select>
      </label>
      <GameSelector
        current={original?.game}
        value={form.game_id}
        onChange={(v) => change("game_id", v)}
      />
    </div>
  );
}
function EventEditor({
  original,
  onClose,
  onSaved,
}: {
  original?: GameEvent;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [form, setForm] = useState<EventForm>(() => formFromEvent(original));
  const [groups, setGroups] = useState<GroupOption[]>([]);
  const [groupError, setGroupError] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    void fetchGroups()
      .then((data) => {
        if (active) setGroups(data);
      })
      .catch((err: unknown) => {
        if (active) setGroupError(message(err));
      });
    return () => {
      active = false;
    };
  }, []);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      const payload = payloadFromForm(form);
      await write(
        original ? `/api/v1/events/${original.id}/` : "/api/v1/events/",
        original ? "PATCH" : "POST",
        payload,
      );
      onClose();
      void onSaved().catch(() => {
        /* Saved successfully; reload manually if refresh fails. */
      });
    } catch (err) {
      setError(message(err));
      setSaving(false);
    }
  }
  return (
    <Modal
      title={original ? "Edit Event" : "Schedule an Event"}
      onClose={() => {
        if (!saving) onClose();
      }}
    >
      <form onSubmit={(e) => void submit(e)}>
        <EventFormFields
          form={form}
          setForm={setForm}
          groups={groups}
          original={original}
        />
        {groupError && (
          <p className="mt-3 text-xs text-amber-300">
            Groups unavailable: {groupError}
          </p>
        )}
        {error && (
          <p role="alert" className="mt-3 text-sm text-red-400">
            {error}
          </p>
        )}
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            disabled={saving}
            onClick={onClose}
            className="rounded-lg border border-slate-600 px-4 py-2 text-sm disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving || !form.title.trim() || !form.starts_at}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold hover:bg-indigo-500 disabled:opacity-50"
          >
            {saving ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              <Check className="h-4 w-4" />
            )}
            {saving ? "Saving..." : original ? "Save Changes" : "Create Event"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function EventArtwork({ event }: { event: GameEvent }) {
  const [imageFailed, setImageFailed] = useState(false);
  const thumbnail = event.game?.thumbnail_url;

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 z-0 overflow-hidden"
    >
      {thumbnail && !imageFailed ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={thumbnail}
          src={thumbnail}
          alt=""
          onError={() => setImageFailed(true)}
          className="h-full w-full object-cover object-center opacity-65"
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-indigo-800 via-violet-800 to-emerald-800">
          <div className="flex items-center gap-5 text-white/20">
            <Dice5 className="h-24 w-24 -rotate-12" />
            <Gamepad2 className="h-20 w-20 rotate-12" />
            <Sparkles className="h-12 w-12" />
          </div>
        </div>
      )}

      <div className="absolute inset-0 bg-gradient-to-r from-slate-950/95 via-slate-950/85 to-slate-950/50" />

      <div className="absolute inset-0 bg-gradient-to-t from-slate-950/75 via-transparent to-slate-950/20" />
    </div>
  );
}

function EventDateBadge({ value }: { value: string }) {
  const date = new Date(value);
  return (
    <div className="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-xl border border-indigo-400/25 bg-indigo-500/15">
      <span className="text-xs font-bold uppercase text-indigo-300">
        {date.toLocaleDateString(undefined, { month: "short" })}
      </span>
      <span className="text-xl font-bold text-white">{date.getDate()}</span>
    </div>
  );
}
function EventMetadata({ event }: { event: GameEvent }) {
  return (
    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-400">
      <span className="inline-flex items-center gap-1.5">
        <CalendarDays className="h-3.5 w-3.5" />
        {dateLabel(event.starts_at)}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <Clock3 className="h-3.5 w-3.5" />
        {timeLabel(event.starts_at)}
      </span>
      {event.location && (
        <span className="inline-flex items-center gap-1.5">
          <MapPin className="h-3.5 w-3.5" />
          {event.location}
        </span>
      )}
      <span className="inline-flex items-center gap-1.5">
        <Users className="h-3.5 w-3.5" />
        {event.going_count} going
      </span>
    </div>
  );
}
function RsvpButtons({
  selected,
  disabled,
  onSelect,
}: {
  selected: RSVPStatus | null;
  disabled: boolean;
  onSelect: (status: RSVPStatus) => void;
}) {
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {RSVP_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          disabled={disabled}
          aria-pressed={selected === option.value}
          onClick={() => onSelect(option.value)}
          className={`rounded-lg border px-3 py-2 text-xs font-semibold disabled:opacity-50 ${
            selected === option.value
              ? "border-indigo-400 bg-indigo-600 text-white"
              : "border-slate-600 bg-slate-800 text-slate-300 hover:border-indigo-400/50"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
function HostActions({
  onEdit,
  onCancel,
}: {
  onEdit: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="mt-3 flex gap-2">
      <button
        type="button"
        onClick={onEdit}
        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-indigo-400"
      >
        <Pencil className="h-3.5 w-3.5" />
        Edit Event
      </button>
      <button
        type="button"
        onClick={onCancel}
        className="inline-flex items-center gap-1.5 rounded-lg border border-red-500/40 px-3 py-2 text-xs font-semibold text-red-300 hover:bg-red-500/10"
      >
        <Trash2 className="h-3.5 w-3.5" />
        Cancel Event
      </button>
    </div>
  );
}
function CancelEventModal({
  event,
  onClose,
  onCancelled,
}: {
  event: GameEvent;
  onClose: () => void;
  onCancelled: () => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  async function confirm() {
    setSaving(true);
    setError("");
    try {
      await write(`/api/v1/events/${event.id}/`, "DELETE");
      onClose();
      void onCancelled().catch(() => {
        /* Delete succeeded; reload if list doesn't refresh. */
      });
    } catch (err) {
      setError(message(err));
      setSaving(false);
    }
  }
  return (
    <Modal
      title="Cancel this event?"
      onClose={() => {
        if (!saving) onClose();
      }}
    >
      <p className="text-sm leading-relaxed text-slate-300">
        This will permanently delete <strong>{event.title}</strong> and its
        RSVPs. This cannot be undone.
      </p>
      {error && (
        <p role="alert" className="mt-3 text-sm text-red-400">
          {error}
        </p>
      )}
      <div className="mt-6 flex justify-end gap-3">
        <button
          type="button"
          disabled={saving}
          onClick={onClose}
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm"
        >
          Keep Event
        </button>
        <button
          type="button"
          disabled={saving}
          onClick={() => void confirm()}
          className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-50"
        >
          {saving ? "Cancelling..." : "Yes, Cancel Event"}
        </button>
      </div>
    </Modal>
  );
}

function EventCardDetails({
  event,
  saving,
  error,
  onEdit,
  onCancel,
  onRsvp,
}: {
  event: GameEvent;
  saving: boolean;
  error: string;
  onEdit: () => void;
  onCancel: () => void;
  onRsvp: (status: RSVPStatus) => void;
}) {
  return (
    <div className="relative z-10 p-5 sm:p-6">
      <div className="flex items-start gap-4">
        <EventDateBadge value={event.starts_at} />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="break-words text-xl font-bold text-white drop-shadow-md">
              {event.title}
            </h3>

            {event.is_host && (
              <span className="rounded-full border border-indigo-400/30 bg-indigo-500/25 px-2.5 py-1 text-xs font-semibold text-indigo-200 backdrop-blur-sm">
                Hosting
              </span>
            )}
          </div>

          {event.description && (
            <p className="mt-3 text-sm leading-relaxed text-slate-200">
              {event.description}
            </p>
          )}

          {event.game && (
            <p className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-indigo-200">
              <Gamepad2 className="h-4 w-4" />
              {event.game.primary_name}
            </p>
          )}

          {event.group && (
            <p className="mt-2 text-xs text-slate-200">
              Group: {event.group.name}
            </p>
          )}

          {event.host && !event.is_host && (
            <p className="mt-2 text-xs text-slate-200">
              Hosted by {event.host.display_name}
            </p>
          )}

          <EventMetadata event={event} />

          {event.is_host && <HostActions onEdit={onEdit} onCancel={onCancel} />}

          <RsvpButtons
            selected={event.my_rsvp}
            disabled={saving}
            onSelect={onRsvp}
          />

          {error && (
            <p role="alert" className="mt-3 text-xs text-red-300">
              {error}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function EventCard({
  event,
  onUpdated,
}: {
  event: GameEvent;
  onUpdated: () => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  async function handleRsvp(status: RSVPStatus) {
    setSaving(true);
    setError("");

    try {
      await write(`/api/v1/events/${event.id}/rsvp/`, "POST", {
        status,
      });
    } catch (err) {
      setError(message(err));
      setSaving(false);
      return;
    }

    try {
      await onUpdated();
    } catch {
      setError("RSVP saved, but the event list could not refresh.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <article className="group relative isolate overflow-hidden rounded-2xl border border-slate-700 bg-zinc-900 transition-all duration-300 hover:border-indigo-400/50 hover:shadow-xl hover:shadow-indigo-500/10">
        <EventArtwork event={event} />

        <EventCardDetails
          event={event}
          saving={saving}
          error={error}
          onEdit={() => setEditing(true)}
          onCancel={() => setCancelling(true)}
          onRsvp={(status) => void handleRsvp(status)}
        />
      </article>

      {editing && (
        <EventEditor
          original={event}
          onClose={() => setEditing(false)}
          onSaved={onUpdated}
        />
      )}

      {cancelling && (
        <CancelEventModal
          event={event}
          onClose={() => setCancelling(false)}
          onCancelled={onUpdated}
        />
      )}
    </>
  );
}

function EventsContent({
  events,
  loading,
  error,
  expanded,
  onCreate,
  onUpdated,
}: {
  events: GameEvent[];
  loading: boolean;
  error: string;
  expanded: boolean;
  onCreate: () => void;
  onUpdated: () => Promise<void>;
}) {
  if (loading)
    return (
      <div role="status" className="space-y-3">
        {[1, 2].map((i) => (
          <div
            key={i}
            className="h-40 animate-pulse rounded-2xl bg-slate-800/50"
          />
        ))}
      </div>
    );
  if (error)
    return (
      <p
        role="alert"
        className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"
      >
        {error}
      </p>
    );
  if (events.length === 0)
    return (
      <div className="rounded-2xl border border-slate-700 bg-zinc-900 p-6 text-center">
        <Dice5 className="mx-auto h-10 w-10 text-indigo-300" />
        <h3 className="mt-3 text-lg font-semibold text-white">
          No upcoming events yet
        </h3>
        <p className="mt-2 text-sm text-slate-400">
          Start planning your next game night!
        </p>
        <button
          type="button"
          onClick={onCreate}
          className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
        >
          Schedule a Game Night
        </button>
      </div>
    );
  return (
    <div className="space-y-4">
      {(expanded ? events : events.slice(0, INITIAL_VISIBLE)).map((event) => (
        <EventCard key={event.id} event={event} onUpdated={onUpdated} />
      ))}
    </div>
  );
}

export default function UpcomingEvents() {
  const [events, setEvents] = useState<GameEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const refreshEvents = useCallback(async () => {
    const result = await fetchEvents();
    setEvents(result);
    setError("");
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void fetchEvents(controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setEvents(result);
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) setError(message(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);
  return (
    <section className="min-w-0 border-t border-gray-600 pt-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-wide sm:text-3xl">
            UPCOMING EVENTS 🎮
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            Plan your next game night with the community.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
        >
          <Plus className="h-4 w-4" />
          Create Event
        </button>
      </div>
      <EventsContent
        events={events}
        loading={loading}
        error={error}
        expanded={expanded}
        onCreate={() => setCreating(true)}
        onUpdated={refreshEvents}
      />
      {!loading && !error && (
        <ShowMoreButton
          expanded={expanded}
          total={events.length}
          initialVisible={INITIAL_VISIBLE}
          onToggle={() => setExpanded((previous) => !previous)}
        />
      )}
      {creating && (
        <EventEditor
          onClose={() => setCreating(false)}
          onSaved={refreshEvents}
        />
      )}
    </section>
  );
}
