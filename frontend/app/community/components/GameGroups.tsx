"use client";

import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  Check,
  Crown,
  LoaderCircle,
  Pencil,
  Plus,
  UserRoundMinus,
  UserRoundPlus,
  Users,
  X,
  LogOut,
} from "lucide-react";
import ShowMoreButton from "./ShowMoreButton";

type Player = {
  user_id: string;
  display_name: string;
};

type GameGroup = {
  id: number;
  name: string;
  description: string;
  owner: Player | null;
  member_count: number;
  is_owner: boolean;
  cover_theme?: string;
};

type GroupDetail = GameGroup & {
  members: Player[];
};

type GroupForm = {
  name: string;
  description: string;
  cover_theme: string;
};

type PendingAction =
  { type: "remove"; member: Player } | { type: "leave" } | null;

const GROUPS_URL = "/api/v1/groups/";
const INITIAL_VISIBLE = 3;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isPlayer(value: unknown): value is Player {
  return (
    isRecord(value) &&
    typeof value.user_id === "string" &&
    typeof value.display_name === "string"
  );
}

function isGroup(value: unknown): value is GameGroup {
  return (
    isRecord(value) &&
    typeof value.id === "number" &&
    typeof value.name === "string" &&
    typeof value.description === "string" &&
    typeof value.member_count === "number" &&
    typeof value.is_owner === "boolean"
  );
}

function isGroupDetail(value: unknown): value is GroupDetail {
  return isGroup(value) && "members" in value && Array.isArray(value.members);
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}

function getInitials(name: string): string {
  return (
    name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "?"
  );
}

function getCsrfToken(): string {
  const cookie = document.cookie
    .split("; ")
    .find(
      (entry) =>
        entry.startsWith("csrftoken=") || entry.startsWith("csrf_token="),
    );

  return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
}

async function request(
  url: string,
  options: RequestInit = {},
): Promise<unknown> {
  const response = await fetch(url, {
    credentials: "same-origin",
    cache: "no-store",
    ...options,
  });

  if (!response.ok) {
    const details = await response.text().catch(() => "");
    const suffix = details.slice(0, 200);

    throw new Error(
      `Request failed (${response.status})${suffix ? `: ${suffix}` : ""}`,
    );
  }

  if (response.status === 204) return null;

  const text = await response.text();
  return text ? (JSON.parse(text) as unknown) : null;
}

function writeRequest(
  url: string,
  method: "POST" | "PATCH" | "DELETE",
  payload?: Record<string, unknown>,
): Promise<unknown> {
  return request(url, {
    method,
    headers: {
      "X-CSRFToken": getCsrfToken(),
      ...(payload ? { "Content-Type": "application/json" } : {}),
    },
    ...(payload ? { body: JSON.stringify(payload) } : {}),
  });
}

async function fetchGroups(): Promise<GameGroup[]> {
  const data = await request(GROUPS_URL);

  if (!Array.isArray(data)) {
    throw new Error("Unexpected groups response.");
  }

  return data.filter(isGroup);
}

async function fetchFriends(): Promise<Player[]> {
  const data = await request("/api/v1/friends/");

  if (!Array.isArray(data)) {
    throw new Error("Unexpected friends response.");
  }

  return data.filter(isPlayer);
}

async function fetchGroupDetail(id: number): Promise<GroupDetail> {
  const data = await request(`${GROUPS_URL}${id}/`);

  if (!isGroupDetail(data)) {
    throw new Error("Unexpected group details response.");
  }

  return {
    ...data,
    members: data.members.filter(isPlayer),
  };
}

function useFriends(enabled: boolean) {
  const [friends, setFriends] = useState<Player[]>([]);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!enabled) return;

    let active = true;

    void fetchFriends()
      .then((result) => {
        if (active) setFriends(result);
      })
      .catch((err: unknown) => {
        if (active) setError(getErrorMessage(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [enabled]);

  return { friends, loading, error };
}

function useSelection() {
  const [selected, setSelected] = useState<string[]>([]);

  function toggle(id: string) {
    setSelected((previous) =>
      previous.includes(id)
        ? previous.filter((item) => item !== id)
        : [...previous, id],
    );
  }

  return { selected, toggle };
}

function Modal({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/75 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 text-slate-100 shadow-2xl"
      >
        <div className="mb-5 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-xl font-bold">{title}</h3>
            {subtitle && (
              <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
            )}
          </div>

          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {children}
      </div>
    </div>
  );
}

function FriendPicker({
  friends,
  selected,
  onToggle,
}: {
  friends: Player[];
  selected: string[];
  onToggle: (id: string) => void;
}) {
  if (friends.length === 0) {
    return (
      <p className="rounded-lg border border-slate-700 bg-slate-800/50 p-4 text-sm text-slate-400">
        No eligible friends to add.
      </p>
    );
  }

  return (
    <div className="max-h-48 space-y-1 overflow-y-auto rounded-xl border border-slate-700 bg-slate-800/40 p-2">
      {friends.map((friend) => {
        const checked = selected.includes(friend.user_id);

        return (
          <label
            key={friend.user_id}
            className="flex cursor-pointer items-center gap-3 rounded-lg p-2 hover:bg-slate-700/50"
          >
            <input
              type="checkbox"
              checked={checked}
              onChange={() => onToggle(friend.user_id)}
              className="h-4 w-4 accent-indigo-500"
            />

            <Avatar name={friend.display_name} />

            <span className="min-w-0 flex-1 truncate text-sm">
              {friend.display_name}
            </span>

            {checked && <Check className="h-4 w-4 text-emerald-400" />}
          </label>
        );
      })}
    </div>
  );
}

function Avatar({ name }: { name: string }) {
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-bold text-indigo-200">
      {getInitials(name)}
    </span>
  );
}

const GROUP_COVERS = [
  { id: "aot", label: "Attack on Titan" },
  { id: "cute", label: "Cute" },
  { id: "deerface", label: "Deer Face" },
  { id: "demslay", label: "Demon Slayer" },
  { id: "eren", label: "Eren" },
  { id: "merry", label: "Merry" },
  { id: "noface", label: "No Face" },
  { id: "onepiece", label: "One Piece" },
  { id: "spirited", label: "Spirited Away" },
  { id: "studio", label: "Studio" },
] as const;

const DEFAULT_GROUP_COVER = "studio";

// Change to true after the Django API accepts and returns cover_theme.
const GROUP_COVER_API_ENABLED = false;

function getGroupArtwork(theme?: string): string {
  const chosen = GROUP_COVERS.find((cover) => cover.id === theme);
  return `/groups/${chosen?.id ?? DEFAULT_GROUP_COVER}.webp`;
}

function GroupCoverPicker({
  selected,
  onChange,
}: {
  selected: string;
  onChange: (theme: string) => void;
}) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-semibold">Choose a Cover</legend>
      <p className="mb-3 text-xs text-slate-400">
        Pick a look for your group. Cover saving will be available once the
        backend is updated.
      </p>

      <div className="grid max-h-64 grid-cols-2 gap-3 overflow-y-auto pr-1 sm:grid-cols-3">
        {GROUP_COVERS.map((cover) => {
          const active = selected === cover.id;

          return (
            <label
              key={cover.id}
              className={`relative cursor-pointer overflow-hidden rounded-xl border-2 transition-colors ${
                active
                  ? "border-indigo-400 ring-2 ring-indigo-500/30"
                  : "border-slate-700 hover:border-indigo-400/60"
              }`}
            >
              <input
                type="radio"
                name="group-cover"
                value={cover.id}
                checked={active}
                onChange={() => onChange(cover.id)}
                className="sr-only"
              />

              <div
                aria-hidden="true"
                className="relative h-24 bg-cover bg-center"
                style={{
                  backgroundImage: `url("${getGroupArtwork(cover.id)}")`,
                }}
              >
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 to-transparent" />

                {active && (
                  <span className="absolute right-2 top-2 rounded-full bg-indigo-500 p-1 text-white">
                    <Check className="h-3.5 w-3.5" />
                  </span>
                )}

                <span className="absolute bottom-2 left-2 right-1 text-xs font-semibold text-white">
                  {cover.label}
                </span>
              </div>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function FormFields({
  form,
  onChange,
}: {
  form: GroupForm;
  onChange: (form: GroupForm) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <label
          htmlFor="group-name"
          className="mb-2 block text-sm font-semibold"
        >
          Group Name
        </label>

        <input
          id="group-name"
          required
          maxLength={150}
          value={form.name}
          onChange={(event) => onChange({ ...form, name: event.target.value })}
          className="w-full rounded-lg border border-slate-600 bg-slate-800 px-4 py-3 text-sm outline-none focus:border-indigo-400"
          placeholder="e.g. Dungeon Dwellers"
        />
      </div>

      <div>
        <label
          htmlFor="group-description"
          className="mb-2 block text-sm font-semibold"
        >
          Description
        </label>

        <textarea
          id="group-description"
          rows={3}
          value={form.description}
          onChange={(event) =>
            onChange({ ...form, description: event.target.value })
          }
          className="w-full resize-none rounded-lg border border-slate-600 bg-slate-800 px-4 py-3 text-sm outline-none focus:border-indigo-400"
          placeholder="What's your group all about?"
        />
      </div>

      <GroupCoverPicker
        selected={form.cover_theme}
        onChange={(cover_theme) => onChange({ ...form, cover_theme })}
      />
    </div>
  );
}

function ActionError({ message }: { message: string }) {
  if (!message) return null;

  return (
    <p role="alert" className="mt-3 text-sm text-red-400">
      {message}
    </p>
  );
}

function CreateGroupModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => Promise<void>;
}) {
  const [form, setForm] = useState<GroupForm>({
    name: "",
    description: "",
    cover_theme: DEFAULT_GROUP_COVER,
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { friends, loading, error: friendsError } = useFriends(true);
  const { selected, toggle } = useSelection();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || !form.name.trim()) return;

    setSaving(true);
    setError("");

    try {
      await writeRequest(GROUPS_URL, "POST", {
        name: form.name.trim(),
        description: form.description.trim(),
        ...(GROUP_COVER_API_ENABLED ? { cover_theme: form.cover_theme } : {}),
        member_ids: selected,
      });

      await onCreated();
      onClose();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      title="Create a Game Group"
      subtitle="Bring your QuestLog friends together."
      onClose={() => {
        if (!saving) onClose();
      }}
    >
      <form onSubmit={(event) => void submit(event)}>
        <FormFields form={form} onChange={setForm} />

        <div className="mb-3 mt-5 flex items-center justify-between">
          <h4 className="text-sm font-semibold">Add Friends (optional)</h4>

          <span className="text-xs text-indigo-300">
            {selected.length} selected
          </span>
        </div>

        {loading ? (
          <p className="text-sm text-slate-400">Loading friends...</p>
        ) : (
          <FriendPicker
            friends={friends}
            selected={selected}
            onToggle={toggle}
          />
        )}

        {friendsError && (
          <p className="mt-2 text-xs text-amber-300">
            Could not load friends: {friendsError}
          </p>
        )}

        <ActionError message={error} />

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
            disabled={saving || !form.name.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold hover:bg-indigo-500 disabled:opacity-50"
          >
            {saving && <LoaderCircle className="h-4 w-4 animate-spin" />}
            Create Group
          </button>
        </div>
      </form>
    </Modal>
  );
}

function EditGroupModal({
  group,
  onClose,
  onUpdated,
}: {
  group: GameGroup;
  onClose: () => void;
  onUpdated: () => Promise<void>;
}) {
  const [form, setForm] = useState<GroupForm>({
    name: group.name,
    description: group.description,
    cover_theme: group.cover_theme ?? DEFAULT_GROUP_COVER,
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || !form.name.trim()) return;

    setSaving(true);
    setError("");

    try {
      await writeRequest(`${GROUPS_URL}${group.id}/`, "PATCH", {
        name: form.name.trim(),
        description: form.description.trim(),
        ...(GROUP_COVER_API_ENABLED ? { cover_theme: form.cover_theme } : {}),
      });

      await onUpdated();
      onClose();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      title="Edit Group"
      subtitle={`Update the details for ${group.name}.`}
      onClose={() => {
        if (!saving) onClose();
      }}
    >
      <form onSubmit={(event) => void submit(event)}>
        <FormFields form={form} onChange={setForm} />

        <ActionError message={error} />

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
            disabled={saving || !form.name.trim()}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold hover:bg-indigo-500 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ConfirmAction({
  action,
  busy,
  onCancel,
  onConfirm,
}: {
  action: Exclude<PendingAction, null>;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const removing = action.type === "remove";
  const label = removing ? "Remove Member" : "Leave Group";

  return (
    <div className="mt-5 rounded-xl border border-red-500/30 bg-red-500/5 p-4">
      <h4 className="font-semibold text-red-300">{label}?</h4>

      <p className="mt-2 text-sm text-slate-300">
        {removing
          ? `Remove ${action.member.display_name} from this group?`
          : "Are you sure you want to leave this group?"}
      </p>

      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={onCancel}
          className="rounded-lg border border-slate-600 px-3 py-2 text-xs disabled:opacity-50"
        >
          Cancel
        </button>

        <button
          type="button"
          disabled={busy}
          onClick={onConfirm}
          className="rounded-lg bg-red-600 px-3 py-2 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-50"
        >
          {busy ? "Please wait..." : label}
        </button>
      </div>
    </div>
  );
}

function MemberList({
  members,
  ownerId,
  canManage,
  onRemove,
}: {
  members: Player[];
  ownerId?: string;
  canManage: boolean;
  onRemove: (member: Player) => void;
}) {
  if (members.length === 0) {
    return (
      <p className="text-sm text-slate-400">No member details available.</p>
    );
  }

  return (
    <div className="space-y-2">
      {members.map((member) => {
        const isOwner = member.user_id === ownerId;

        return (
          <div
            key={member.user_id}
            className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-800/50 p-3"
          >
            <Avatar name={member.display_name} />

            <span className="min-w-0 flex-1 truncate text-sm font-medium">
              {member.display_name}
            </span>

            {isOwner && (
              <span className="inline-flex items-center gap-1 text-xs text-amber-300">
                <Crown className="h-3 w-3" />
                Owner
              </span>
            )}

            {canManage && !isOwner && (
              <button
                type="button"
                onClick={() => onRemove(member)}
                aria-label={`Remove ${member.display_name}`}
                className="rounded-lg p-2 text-slate-400 hover:bg-red-500/10 hover:text-red-300"
                title="Remove member"
              >
                <UserRoundMinus className="h-4 w-4" />
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

function AddFriendsPanel({
  friends,
  friendsLoading,
  friendsError,
  selected,
  toggle,
  busy,
  onAdd,
}: {
  friends: Player[];
  friendsLoading: boolean;
  friendsError: string;
  selected: string[];
  toggle: (id: string) => void;
  busy: boolean;
  onAdd: () => void;
}) {
  return (
    <div className="mt-5 border-t border-slate-700 pt-4">
      <h4 className="mb-3 text-sm font-semibold">Select friends to add</h4>

      {friendsLoading ? (
        <p className="text-sm text-slate-400">Loading friends...</p>
      ) : (
        <FriendPicker friends={friends} selected={selected} onToggle={toggle} />
      )}

      {friendsError && (
        <p className="mt-2 text-xs text-amber-300">{friendsError}</p>
      )}

      <button
        type="button"
        disabled={busy || friendsLoading || selected.length === 0}
        onClick={onAdd}
        className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold hover:bg-indigo-500 disabled:opacity-50"
      >
        {busy ? "Adding..." : "Add Selected Friends"}
      </button>
    </div>
  );
}

function MembersPanel({
  detail,
  group,
  busy,
  friends,
  friendsLoading,
  friendsError,
  selected,
  toggle,
  showAdd,
  setShowAdd,
  setPending,
  onAdd,
}: {
  detail: GroupDetail;
  group: GameGroup;
  busy: boolean;
  friends: Player[];
  friendsLoading: boolean;
  friendsError: string;
  selected: string[];
  toggle: (id: string) => void;
  showAdd: boolean;
  setShowAdd: (value: boolean) => void;
  setPending: (action: PendingAction) => void;
  onAdd: () => void;
}) {
  const existingIds = new Set(detail.members.map((member) => member.user_id));

  const eligibleFriends = friends.filter(
    (friend) => !existingIds.has(friend.user_id),
  );

  const eligibleSelected = selected.filter((id) => !existingIds.has(id));

  function handleToggleAdd() {
    setPending(null);
    setShowAdd(!showAdd);
  }

  function handleRemove(member: Player) {
    setShowAdd(false);
    setPending({ type: "remove", member });
  }

  function handleLeave() {
    setPending({ type: "leave" });
  }

  return (
    <>
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="text-sm text-slate-400">
          {detail.member_count}{" "}
          {detail.member_count === 1 ? "member" : "members"}
        </p>

        {group.is_owner && (
          <button
            type="button"
            disabled={busy}
            onClick={handleToggleAdd}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold hover:bg-indigo-500 disabled:opacity-50"
          >
            <UserRoundPlus className="h-4 w-4" />
            Add Friends
          </button>
        )}
      </div>

      <div className="max-h-56 overflow-y-auto">
        <MemberList
          members={detail.members}
          ownerId={detail.owner?.user_id}
          canManage={group.is_owner}
          onRemove={handleRemove}
        />
      </div>

      {showAdd && group.is_owner && (
        <AddFriendsPanel
          friends={eligibleFriends}
          friendsLoading={friendsLoading}
          friendsError={friendsError}
          selected={eligibleSelected}
          toggle={toggle}
          busy={busy}
          onAdd={onAdd}
        />
      )}

      {!group.is_owner && (
        <div className="mt-5 border-t border-slate-700 pt-4">
          <button
            type="button"
            disabled={busy}
            onClick={handleLeave}
            className="inline-flex items-center gap-2 rounded-lg border border-red-500/30 px-3 py-2 text-sm text-red-300 hover:bg-red-500/10 disabled:opacity-50"
          >
            <LogOut className="h-4 w-4" />
            Leave Group
          </button>
        </div>
      )}
    </>
  );
}

function GroupMembersModal({
  group,
  onClose,
  onUpdated,
}: {
  group: GameGroup;
  onClose: () => void;
  onUpdated: () => Promise<void>;
}) {
  const [detail, setDetail] = useState<GroupDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [pending, setPending] = useState<PendingAction>(null);

  const {
    friends,
    loading: friendsLoading,
    error: friendsError,
  } = useFriends(group.is_owner);

  const { selected, toggle } = useSelection();

  const refreshDetail = useCallback(async () => {
    const result = await fetchGroupDetail(group.id);
    setDetail(result);
  }, [group.id]);

  useEffect(() => {
    let active = true;

    void fetchGroupDetail(group.id)
      .then((result) => {
        if (active) setDetail(result);
      })
      .catch((err: unknown) => {
        if (active) setError(getErrorMessage(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [group.id]);

  async function runAction(operation: () => Promise<void>) {
    setBusy(true);
    setError("");

    try {
      await operation();
      await refreshDetail();
      await onUpdated();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleAdd() {
    if (!group.is_owner || selected.length === 0) return;

    const existingIds = new Set(
      detail?.members.map((member) => member.user_id) ?? [],
    );

    await runAction(async () => {
      for (const userId of selected) {
        if (existingIds.has(userId)) continue;

        await writeRequest(`${GROUPS_URL}${group.id}/members/`, "POST", {
          user_id: userId,
        });
      }
    });

    setShowAdd(false);
  }

  async function handleConfirmedAction() {
    if (!pending) return;

    const action = pending;

    if (action.type === "leave") {
      setBusy(true);
      setError("");

      try {
        await writeRequest(`${GROUPS_URL}${group.id}/leave/`, "POST");

        await onUpdated();
        onClose();
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setBusy(false);
        setPending(null);
      }

      return;
    }

    await runAction(async () => {
      await writeRequest(
        `${GROUPS_URL}${group.id}/members/${action.member.user_id}/`,
        "DELETE",
      );
    });

    setPending(null);
  }

  return (
    <Modal
      title={group.name}
      subtitle="View and manage group membership."
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      {loading && <p className="text-sm text-slate-400">Loading members...</p>}

      {detail && (
        <MembersPanel
          detail={detail}
          group={group}
          busy={busy}
          friends={friends}
          friendsLoading={friendsLoading}
          friendsError={friendsError}
          selected={selected}
          toggle={toggle}
          showAdd={showAdd}
          setShowAdd={setShowAdd}
          setPending={setPending}
          onAdd={() => void handleAdd()}
        />
      )}

      {pending && (
        <ConfirmAction
          action={pending}
          busy={busy}
          onCancel={() => setPending(null)}
          onConfirm={() => void handleConfirmedAction()}
        />
      )}

      <ActionError message={error} />

      <div className="mt-6 flex justify-end">
        <button
          type="button"
          disabled={busy}
          onClick={onClose}
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm hover:bg-slate-800 disabled:opacity-50"
        >
          Close
        </button>
      </div>
    </Modal>
  );
}

function GroupCard({
  group,
  onMembers,
  onEdit,
}: {
  group: GameGroup;
  onMembers: (group: GameGroup) => void;
  onEdit: (group: GameGroup) => void;
}) {
  const artwork = getGroupArtwork(group.cover_theme);

  return (
    <article className="group relative isolate overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 transition-all duration-300 hover:border-indigo-400/50 hover:shadow-xl hover:shadow-indigo-500/10">
      {/* Full-card background */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 z-0 bg-cover bg-center opacity-70 transition-transform duration-500 group-hover:scale-105"
        style={{
          backgroundImage: `url("${artwork}")`,
        }}
      />

      {/* Gradient for readability */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 z-0 bg-gradient-to-r from-slate-950/95 via-slate-950/80 to-slate-950/45"
      />

      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 z-0 bg-gradient-to-t from-slate-950/85 via-transparent to-slate-950/20"
      />

      {/* Group information */}
      <div className="relative z-10 flex min-h-52 items-start gap-3 p-5">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-indigo-400/30 bg-indigo-500/25 backdrop-blur-sm">
          <Users className="h-6 w-6 text-indigo-200" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="break-words text-xl font-bold text-white drop-shadow-md">
              {group.name}
            </h3>

            {group.is_owner && (
              <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/30 bg-amber-500/20 px-2.5 py-1 text-xs font-semibold text-amber-200 backdrop-blur-sm">
                <Crown className="h-3 w-3" />
                Owner
              </span>
            )}
          </div>

          {group.description && (
            <p className="mt-3 text-sm leading-relaxed text-slate-200">
              {group.description}
            </p>
          )}

          <p className="mt-3 inline-flex items-center gap-2 text-xs font-medium text-slate-200">
            <Users className="h-4 w-4" />
            {group.member_count}{" "}
            {group.member_count === 1 ? "member" : "members"}
          </p>

          <div className="mt-5 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => onMembers(group)}
              className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-slate-900/70 px-3 py-2 text-xs font-semibold text-white backdrop-blur-sm transition-colors hover:border-indigo-400 hover:bg-slate-800"
            >
              <Users className="h-3.5 w-3.5" />
              View Members
            </button>

            {group.is_owner && (
              <>
                <button
                  type="button"
                  onClick={() => onMembers(group)}
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-indigo-500"
                >
                  <UserRoundPlus className="h-3.5 w-3.5" />
                  Add Friends
                </button>

                <button
                  type="button"
                  onClick={() => onEdit(group)}
                  className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-slate-900/70 px-3 py-2 text-xs font-semibold text-white backdrop-blur-sm transition-colors hover:border-indigo-400 hover:bg-slate-800"
                >
                  <Pencil className="h-3.5 w-3.5" />
                  Edit
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}

function GroupsContent({
  groups,
  loading,
  error,
  expanded,
  onCreate,
  onMembers,
  onEdit,
}: {
  groups: GameGroup[];
  loading: boolean;
  error: string;
  expanded: boolean;
  onCreate: () => void;
  onMembers: (group: GameGroup) => void;
  onEdit: (group: GameGroup) => void;
}) {
  if (loading) {
    return <p className="text-sm text-slate-400">Loading game groups...</p>;
  }

  if (error && groups.length === 0) {
    return <ActionError message={error} />;
  }

  if (groups.length === 0) {
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-7 text-center">
        <Users className="mx-auto h-9 w-9 text-indigo-300" />

        <h3 className="mt-3 text-lg font-semibold">No game groups yet</h3>

        <p className="mt-2 text-sm text-slate-400">
          Create a group and bring your friends together.
        </p>

        <button
          type="button"
          onClick={onCreate}
          className="mt-5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold hover:bg-indigo-500"
        >
          Create Your First Group
        </button>
      </div>
    );
  }

  const visibleGroups = expanded ? groups : groups.slice(0, INITIAL_VISIBLE);

  return (
    <div className="space-y-3">
      {visibleGroups.map((group) => (
        <GroupCard
          key={group.id}
          group={group}
          onMembers={onMembers}
          onEdit={onEdit}
        />
      ))}

      <ActionError message={error} />
    </div>
  );
}

export default function GameGroups() {
  const [groups, setGroups] = useState<GameGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<GameGroup | null>(null);
  const [editingGroup, setEditingGroup] = useState<GameGroup | null>(null);

  const [expanded, setExpanded] = useState(false);

  const refreshGroups = useCallback(async () => {
    const result = await fetchGroups();
    setGroups(result);
    setError("");
  }, []);

  useEffect(() => {
    let active = true;

    void fetchGroups()
      .then((result) => {
        if (active) setGroups(result);
      })
      .catch((err: unknown) => {
        if (active) setError(getErrorMessage(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="min-w-0">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-bold tracking-wide sm:text-3xl">
          YOUR GAME GROUPS
        </h2>

        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
        >
          <Plus className="h-4 w-4" />
          Create Group
        </button>
      </div>

      <GroupsContent
        groups={groups}
        loading={loading}
        error={error}
        expanded={expanded}
        onCreate={() => setCreateOpen(true)}
        onMembers={setSelectedGroup}
        onEdit={setEditingGroup}
      />

      {!loading && !error && (
        <ShowMoreButton
          expanded={expanded}
          total={groups.length}
          initialVisible={INITIAL_VISIBLE}
          onToggle={() => setExpanded((previous) => !previous)}
        />
      )}

      {createOpen && (
        <CreateGroupModal
          onClose={() => setCreateOpen(false)}
          onCreated={refreshGroups}
        />
      )}

      {selectedGroup && (
        <GroupMembersModal
          group={selectedGroup}
          onClose={() => setSelectedGroup(null)}
          onUpdated={refreshGroups}
        />
      )}

      {editingGroup && (
        <EditGroupModal
          group={editingGroup}
          onClose={() => setEditingGroup(null)}
          onUpdated={refreshGroups}
        />
      )}
    </section>
  );
}
