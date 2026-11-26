"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { chatRequest, messageOf } from "./api";
import type { ChatPreferences, Player } from "./types";

type BooleanPreference = Exclude<keyof ChatPreferences, "who_can_message">;
const toggles: {
  key: BooleanPreference;
  title: string;
  description: string;
}[] = [
  {
    key: "show_online_status",
    title: "Show my online status",
    description:
      "Let people you can chat with see when you are active in QuestLog. Turning this off also hides their status from you.",
  },
  {
    key: "send_read_receipts",
    title: "Send read receipts",
    description:
      "Show Read only when both people allow receipts. Unread counts still work when this is off.",
  },
  {
    key: "message_notifications",
    title: "Message notifications",
    description:
      "Show an in-app notification for new messages while QuestLog is open. This does not enable browser or email notifications.",
  },
  {
    key: "allow_friend_requests",
    title: "Allow friend requests",
    description:
      "Allow new friend requests. You can still answer requests already received.",
  },
  {
    key: "mature_language_filter",
    title: "Mature-language filtering",
    description:
      "Mask a limited list of explicit English words in messages and previews you view. This does not cover every word or language.",
  },
];

function PreferenceFields({
  value,
  disabled,
  onChange,
}: {
  value: ChatPreferences;
  disabled: boolean;
  onChange: (next: ChatPreferences) => void;
}) {
  return (
    <>
      <div className="divide-y divide-border">
        {toggles.map((item) => (
          <label
            key={item.key}
            className="flex cursor-pointer items-start justify-between gap-5 py-5"
          >
            <span>
              <span className="block font-semibold">{item.title}</span>
              <span className="mt-1 block text-sm text-muted">
                {item.description}
              </span>
            </span>
            <input
              type="checkbox"
              role="switch"
              checked={value[item.key]}
              disabled={disabled}
              onChange={(event) =>
                onChange({ ...value, [item.key]: event.target.checked })
              }
              className="mt-1 h-5 w-5 shrink-0 accent-indigo-600"
            />
          </label>
        ))}
      </div>
      <fieldset
        disabled={disabled}
        className="mt-6 border-t border-border pt-5"
      >
        <legend className="px-1 font-bold">Who can message you?</legend>
        <div className="mt-3 flex flex-wrap gap-5">
          {(
            [
              ["EVERYONE", "Everyone"],
              ["FRIENDS", "Friends only"],
              ["NOBODY", "Nobody"],
            ] as const
          ).map(([permission, label]) => (
            <label key={permission} className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="message-permission"
                value={permission}
                checked={value.who_can_message === permission}
                onChange={() =>
                  onChange({ ...value, who_can_message: permission })
                }
                className="accent-indigo-600"
              />
              {label}
            </label>
          ))}
        </div>
        <p className="mt-3 text-xs text-muted">
          This controls new incoming messages, including replies in existing
          chats. Blocking always takes priority. Existing history remains
          available.
        </p>
      </fieldset>
    </>
  );
}

function BlockedAccounts({
  accounts,
  busy,
  onUnblock,
}: {
  accounts: Player[];
  busy: boolean;
  onUnblock: (id: string) => Promise<void>;
}) {
  return (
    <section className="mt-6 rounded-2xl border border-border bg-surface p-6">
      <h3 className="text-xl font-bold">Blocked Accounts</h3>
      <p className="mt-2 text-sm text-muted">
        Block a player from their conversation header. A block prevents
        messages, online status and read receipts in both directions.
      </p>
      {accounts.length === 0 ? (
        <p className="mt-5 text-sm text-muted">No blocked accounts.</p>
      ) : (
        <ul className="mt-5 divide-y divide-border">
          {accounts.map((player, index) => (
            <li
              key={player.user_id ?? index}
              className="flex items-center justify-between gap-4 py-3"
            >
              <span>{player.display_name}</span>
              {player.user_id && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    if (player.user_id) void onUnblock(player.user_id);
                  }}
                  className="rounded-xl border border-border px-4 py-2 text-sm font-semibold hover:bg-surface-hover disabled:opacity-50"
                >
                  Unblock
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function ChatSettings() {
  const [value, setValue] = useState<ChatPreferences | null>(null);
  const [saved, setSaved] = useState<ChatPreferences | null>(null);
  const [accounts, setAccounts] = useState<Player[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const running = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const [preferences, blocks] = await Promise.all([
          chatRequest<ChatPreferences>("/preferences/", {
            signal: controller.signal,
          }),
          chatRequest<Player[]>("/blocks/", { signal: controller.signal }),
        ]);
        if (!controller.signal.aborted) {
          setValue(preferences);
          setSaved(preferences);
          setAccounts(blocks);
        }
      } catch (caught) {
        if (!controller.signal.aborted) setError(messageOf(caught));
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  async function save() {
    if (!value || running.current) return;
    running.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await chatRequest<ChatPreferences>("/preferences/", {
        method: "PATCH",
        body: value,
      });
      setValue(updated);
      setSaved(updated);
      setMessage("Chat preferences saved.");
    } catch (caught) {
      setError(messageOf(caught));
    } finally {
      running.current = false;
      setBusy(false);
    }
  }
  async function unblock(id: string) {
    if (running.current) return;
    running.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await chatRequest(`/blocks/${id}/`, { method: "DELETE" });
      setAccounts((old) => old.filter((player) => player.user_id !== id));
      setMessage("Player unblocked.");
    } catch (caught) {
      setError(messageOf(caught));
    } finally {
      running.current = false;
      setBusy(false);
    }
  }
  return (
    <section>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-3xl font-black">CHAT &amp; MESSAGING</h2>
        <Link href="/chat" className="font-semibold text-link">
          Open Weeple Chat →
        </Link>
      </div>
      {error && (
        <p
          role="alert"
          className="mb-4 text-sm text-red-400 [html[data-theme=light]_&]:text-red-700"
        >
          {error}
        </p>
      )}
      {value ? (
        <div className="rounded-2xl border border-border bg-surface p-6">
          <h3 className="text-xl font-bold">Messaging Preferences</h3>
          <PreferenceFields
            value={value}
            disabled={busy}
            onChange={(next) => {
              setValue(next);
              setMessage("");
            }}
          />
          <button
            type="button"
            disabled={busy || JSON.stringify(value) === JSON.stringify(saved)}
            onClick={() => void save()}
            className="mt-6 rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {busy ? "Saving..." : "Save Chat Preferences"}
          </button>
        </div>
      ) : (
        <p className="text-sm text-muted">
          {error
            ? "Chat settings are unavailable. Reload this page to retry."
            : "Loading chat settings..."}
        </p>
      )}
      {message && (
        <p
          role="status"
          className="mt-4 text-sm text-emerald-400 [html[data-theme=light]_&]:text-emerald-700"
        >
          {message}
        </p>
      )}
      {value && (
        <BlockedAccounts accounts={accounts} busy={busy} onUnblock={unblock} />
      )}
    </section>
  );
}
