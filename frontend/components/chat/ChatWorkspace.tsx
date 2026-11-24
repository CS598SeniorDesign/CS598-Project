"use client";

import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { chatRequest, mergeConversations, messageOf } from "./api";
import { useConversation } from "./useConversation";
import { useChatSummary } from "./ChatProvider";
import type { ChatMessage, Conversation, Player, Results } from "./types";

function Avatar({ player }: { player: Player }) {
  const avatar = /^\/avatars\/avatar(?:[1-9]|1[0-2])\.webp$/.test(player.avatar)
    ? player.avatar
    : "/avatars/avatar1.webp";
  return (
    <Image
      src={avatar}
      alt=""
      width={44}
      height={44}
      className="h-11 w-11 shrink-0 rounded-full border border-border object-cover"
    />
  );
}
function PresenceAvatar({
  player,
  online,
}: {
  player: Player;
  online: boolean | null;
}) {
  return (
    <span className="relative inline-flex shrink-0">
      <Avatar player={player} />
      {online !== null && (
        <span
          role="img"
          aria-label={online ? "Online" : "Offline"}
          title={online ? "Online" : "Offline"}
          className={`absolute bottom-0 right-0 h-3 w-3 rounded-full ring-2 ring-surface ${online ? "bg-emerald-400 [html[data-theme=light]_&]:bg-emerald-600" : "bg-slate-400 [html[data-theme=light]_&]:bg-slate-500"}`}
        />
      )}
    </span>
  );
}

function PresenceLabel({ online }: { online: boolean | null }) {
  if (online === null) return null;
  return (
    <p
      className={`mt-0.5 text-xs font-medium ${online ? "text-emerald-400 [html[data-theme=light]_&]:text-emerald-700" : "text-muted"}`}
    >
      {online ? "Online" : "Offline"}
    </p>
  );
}

function time(value: string) {
  return new Date(value).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

function ConversationButton({
  conversation,
  selected,
  onSelect,
}: {
  conversation: Conversation;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={selected ? "true" : undefined}
      className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left transition ${selected ? "border-indigo-500 bg-indigo-500/10" : "border-transparent hover:bg-surface-hover"}`}
    >
      <PresenceAvatar
        player={conversation.other}
        online={conversation.online}
      />
      <span className="min-w-0 flex-1">
        <span className="block truncate font-semibold">
          {conversation.other.display_name}
        </span>
        <span className="block truncate text-xs text-muted">
          {conversation.last_message?.body ?? "Start a conversation"}
        </span>
      </span>
      {conversation.unread_count > 0 && (
        <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-xs text-white">
          {conversation.unread_count}
        </span>
      )}
    </button>
  );
}

function ConversationSidebar({
  conversations,
  selected,
  onSelect,
  onOpen,
  hasMore,
  onMore,
}: {
  conversations: Conversation[];
  selected: number | null;
  onSelect: (id: number) => void;
  onOpen: (userId: string) => Promise<void>;
  hasMore: boolean;
  onMore: () => void;
}) {
  const [search, setSearch] = useState("");
  const [contacts, setContacts] = useState<Results<Player>>({
    results: [],
    has_more: false,
  });
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      try {
        const result = await chatRequest<Results<Player>>(
          `/contacts/?search=${encodeURIComponent(search.trim())}`,
          { signal: controller.signal },
        );
        if (!controller.signal.aborted) {
          setContacts(result);
          setError("");
        }
      } catch (caught) {
        if (!controller.signal.aborted) setError(messageOf(caught));
      }
    }, 300);
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [search]);
  return (
    <aside
      className={`min-h-0 flex-col border-border bg-surface p-4 lg:flex lg:border-r ${selected === null ? "flex" : "hidden"}`}
    >
      <h2 className="mb-4 text-2xl font-bold">Chats</h2>
      <label className="text-sm font-medium">
        Find a player
        <input
          type="search"
          maxLength={100}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search display names"
          className="mt-2 w-full rounded-xl border border-border bg-input px-3 py-2 text-foreground"
        />
      </label>
      <div className="mt-4 min-h-0 flex-1 space-y-4 overflow-y-auto">
        {error && (
          <p
            role="alert"
            className="text-sm text-red-400 [html[data-theme=light]_&]:text-red-700"
          >
            {error}
          </p>
        )}
        <section aria-label="Conversations" className="space-y-1">
          {conversations.map((conversation) => (
            <ConversationButton
              key={conversation.id}
              conversation={conversation}
              selected={selected === conversation.id}
              onSelect={() => onSelect(conversation.id)}
            />
          ))}
          {conversations.length === 0 && (
            <p className="p-3 text-sm text-muted">
              No conversations yet. Choose a friend below to say hello.
            </p>
          )}
          {hasMore && (
            <button
              type="button"
              onClick={onMore}
              className="px-3 py-2 text-sm text-link"
            >
              Load more conversations
            </button>
          )}
        </section>
        <section
          aria-label="Start a conversation"
          className="border-t border-border pt-4"
        >
          <h3 className="mb-2 text-sm font-bold">
            {search.trim() ? "Players" : "Your friends"}
          </h3>
          {contacts.results.map((player) => (
            <button
              key={player.user_id}
              type="button"
              disabled={!player.can_send}
              onClick={() => {
                if (player.user_id) void onOpen(player.user_id);
              }}
              className="flex w-full items-center gap-3 rounded-xl p-2 text-left hover:bg-surface-hover disabled:opacity-50"
            >
              <Avatar player={player} />
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold">
                  {player.display_name}
                </span>
                <span className="text-xs text-muted">
                  {player.can_send ? "Message" : "Messaging unavailable"}
                </span>
              </span>
            </button>
          ))}
          {contacts.has_more && (
            <p className="text-xs text-muted">
              Showing the first 50 players. Narrow your search to find someone.
            </p>
          )}
        </section>
      </div>
    </aside>
  );
}

function MessageBubble({
  message,
  receipts,
}: {
  message: ChatMessage;
  receipts: boolean;
}) {
  return (
    <li className={`flex ${message.mine ? "justify-end" : "justify-start"}`}>
      <div className="max-w-[85%] sm:max-w-[75%]">
        <p
          className={`whitespace-pre-wrap break-words rounded-2xl px-4 py-3 text-sm leading-relaxed [overflow-wrap:anywhere] ${message.mine ? "rounded-br-sm bg-indigo-600 text-white" : "rounded-bl-sm border border-border bg-surface-hover text-foreground"}`}
        >
          {message.body}
        </p>
        <p
          className={`mt-1 text-xs text-muted ${message.mine ? "text-right" : "text-left"}`}
        >
          <time
            dateTime={message.created_at}
            title={new Date(message.created_at).toLocaleString()}
          >
            {time(message.created_at)}
          </time>
          {message.mine && receipts && message.is_read === true && " · Read"}
        </p>
      </div>
    </li>
  );
}

function MessageStream({
  messages,
  receipts,
  onAtBottom,
  hasOlder,
  loadOlder,
  loadingOlder,
}: {
  messages: ChatMessage[];
  receipts: boolean;
  onAtBottom: (value: boolean) => void;
  hasOlder: boolean;
  loadOlder: () => Promise<void>;
  loadingOlder: boolean;
}) {
  const container = useRef<HTMLDivElement>(null);
  const stick = useRef(true);
  const lastId = messages[messages.length - 1]?.id;
  useEffect(() => {
    if (stick.current && container.current)
      container.current.scrollTop = container.current.scrollHeight;
  }, [lastId]);
  async function older() {
    const element = container.current;
    if (!element) return;
    stick.current = false;
    onAtBottom(false);
    const before = element.scrollHeight;
    await loadOlder();
    requestAnimationFrame(() => {
      if (container.current)
        container.current.scrollTop += container.current.scrollHeight - before;
    });
  }
  return (
    <div
      ref={container}
      onScroll={(event) => {
        const element = event.currentTarget;
        stick.current =
          element.scrollHeight - element.scrollTop - element.clientHeight < 60;
        onAtBottom(stick.current);
      }}
      className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6"
      aria-label="Message history"
    >
      {hasOlder && (
        <button
          type="button"
          disabled={loadingOlder}
          onClick={() => void older()}
          className="mx-auto mb-5 block rounded-lg border border-border px-4 py-2 text-sm text-link disabled:opacity-50"
        >
          {loadingOlder ? "Loading..." : "Load earlier messages"}
        </button>
      )}
      {messages.length === 0 && (
        <p className="py-10 text-center text-sm text-muted">
          No messages yet. Start the conversation below.
        </p>
      )}
      <ol className="space-y-4">
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            receipts={receipts}
          />
        ))}
      </ol>
    </div>
  );
}

function Composer({
  canSend,
  busy,
  onSend,
}: {
  canSend: boolean;
  busy: boolean;
  onSend: (body: string) => Promise<boolean>;
}) {
  const [draft, setDraft] = useState("");
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = draft.trim();
    if (!body || busy || !canSend) return;
    if (await onSend(body)) setDraft("");
  }
  return (
    <form
      onSubmit={(event) => void submit(event)}
      className="border-t border-border bg-surface p-4"
    >
      <label htmlFor="chat-message" className="sr-only">
        Message
      </label>
      <div className="flex items-end gap-3">
        <textarea
          id="chat-message"
          rows={2}
          maxLength={2000}
          disabled={!canSend || busy}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={
            canSend
              ? "Write a message..."
              : "Messaging is unavailable for this conversation."
          }
          className="min-w-0 flex-1 resize-none rounded-xl border border-border bg-input px-4 py-3 text-foreground outline-none focus:border-indigo-500 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={!canSend || busy || !draft.trim()}
          className="rounded-xl bg-indigo-600 px-5 py-3 font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {busy ? "Sending..." : "Send"}
        </button>
      </div>
      <p className="mt-2 text-right text-xs text-muted">{draft.length}/2000</p>
    </form>
  );
}

function ConversationHeader({
  conversation,
  onBack,
  onBlock,
}: {
  conversation: Conversation;
  onBack: () => void;
  onBlock: () => Promise<void>;
}) {
  return (
    <header className="flex items-center gap-3 border-b border-border bg-surface p-4">
      <button
        type="button"
        onClick={onBack}
        className="rounded-lg border border-border px-3 py-2 text-sm lg:hidden"
        aria-label="Back to conversations"
      >
        Back
      </button>
      <PresenceAvatar
        player={conversation.other}
        online={conversation.online}
      />
      <div className="min-w-0 flex-1">
        <h2 className="truncate font-bold">
          {conversation.other.display_name}
        </h2>
        <PresenceLabel online={conversation.online} />
      </div>
      {conversation.other.user_id && (
        <button
          type="button"
          onClick={() => void onBlock()}
          className="rounded-lg border border-border px-3 py-2 text-xs font-semibold hover:bg-surface-hover"
        >
          {conversation.blocked_by_me ? "Unblock" : "Block"}
        </button>
      )}
    </header>
  );
}

export default function ChatWorkspace() {
  const { userId, ready } = useChatSummary();
  if (userId) return <AuthenticatedWorkspace key={userId} />;
  return (
    <section className="mx-auto max-w-4xl p-8 text-foreground">
      <h1 className="text-3xl font-bold">Weeple Chat</h1>
      <p role="status" className="mt-4 text-muted">
        {ready
          ? "Chat is unavailable. Sign in or reload to try again."
          : "Loading your chat account..."}
      </p>
      <Link href="/login" className="mt-4 inline-block text-link">
        Sign in
      </Link>
    </section>
  );
}

function AuthenticatedWorkspace() {
  const params = useSearchParams();
  const userId = params.get("user");
  const [selected, setSelected] = useState<number | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState("");
  const [atBottom, setAtBottom] = useState(true);
  const opening = useRef(false);
  const loadedBeyondFirstPage = useRef(false);
  const thread = useConversation(selected, atBottom);

  const openChat = useCallback(async (target: string) => {
    if (opening.current) return;
    opening.current = true;
    try {
      const conversation = await chatRequest<Conversation>("/conversations/", {
        method: "POST",
        body: { user_id: target },
      });
      setConversations((old) => mergeConversations(old, [conversation]));
      setSelected(conversation.id);
      setAtBottom(true);
      setError("");
    } catch (caught) {
      setError(messageOf(caught));
    } finally {
      opening.current = false;
    }
  }, []);

  useEffect(() => {
    if (!userId) return;
    const controller = new AbortController();
    void chatRequest<Conversation>("/conversations/", {
      method: "POST",
      body: { user_id: userId },
      signal: controller.signal,
    })
      .then((conversation) => {
        if (controller.signal.aborted) return;
        setConversations((old) => mergeConversations(old, [conversation]));
        setSelected(conversation.id);
        setAtBottom(true);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(messageOf(caught));
      });
    return () => controller.abort();
  }, [userId]);
  useEffect(() => {
    const controller = new AbortController();
    let listPending = false;
    async function load() {
      if (listPending || document.visibilityState !== "visible") return;
      listPending = true;
      try {
        const result = await chatRequest<Results<Conversation>>(
          "/conversations/",
          { signal: controller.signal },
        );
        if (!controller.signal.aborted) {
          setConversations((old) => mergeConversations(old, result.results));
          if (!loadedBeyondFirstPage.current) setHasMore(result.has_more);
          setError("");
        }
      } catch (caught) {
        if (!controller.signal.aborted) setError(messageOf(caught));
      } finally {
        listPending = false;
      }
    }
    void load();
    const interval = window.setInterval(() => void load(), 10000);
    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, []);

  async function moreConversations() {
    loadedBeyondFirstPage.current = true;
    try {
      const result = await chatRequest<Results<Conversation>>(
        `/conversations/?offset=${conversations.length}`,
      );
      setConversations((old) => mergeConversations(old, result.results));
      setHasMore(result.has_more);
    } catch (caught) {
      setError(messageOf(caught));
    }
  }
  async function toggleBlock() {
    const conversation = thread.current?.conversation;
    const other = conversation?.other.user_id;
    if (!conversation || !other) return;
    try {
      if (conversation.blocked_by_me)
        await chatRequest(`/blocks/${other}/`, { method: "DELETE" });
      else
        await chatRequest("/blocks/", {
          method: "POST",
          body: { user_id: other },
        });
      await thread.reload();
    } catch (caught) {
      setError(messageOf(caught));
    }
  }

  const current = thread.current;
  return (
    <section className="mx-auto max-w-[1500px] px-3 py-6 text-foreground sm:px-6 lg:px-10">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-extrabold">Weeple Chat</h1>
          <p className="mt-1 text-sm text-muted">
            A place to plan your next game night.
          </p>
        </div>
        <div className="flex gap-4 text-sm font-semibold text-link">
          <Link href="/dashboardPpt">Dashboard</Link>
          <Link href="/community">Weeple</Link>
          <Link href="/settings?tab=chat">Chat settings</Link>
        </div>
      </header>
      {error && (
        <p
          role="alert"
          className="mb-4 rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-400 [html[data-theme=light]_&]:text-red-700"
        >
          {error}{" "}
          <Link href="/login" className="underline">
            Sign in
          </Link>
        </p>
      )}
      <div className="grid h-[min(780px,78dvh)] min-h-[450px] overflow-hidden rounded-2xl border border-border bg-background shadow-sm lg:grid-cols-[310px_minmax(0,1fr)]">
        <ConversationSidebar
          conversations={conversations}
          selected={selected}
          onSelect={(id) => {
            setSelected(id);
            setAtBottom(true);
          }}
          onOpen={openChat}
          hasMore={hasMore}
          onMore={() => void moreConversations()}
        />
        <div
          className={`min-h-0 min-w-0 flex-col ${selected === null ? "hidden lg:flex" : "flex"}`}
        >
          {current ? (
            <>
              <ConversationHeader
                conversation={current.conversation}
                onBack={() => setSelected(null)}
                onBlock={toggleBlock}
              />
              <MessageStream
                key={`messages-${current.id}`}
                messages={current.messages}
                receipts={current.conversation.read_receipts_visible}
                onAtBottom={setAtBottom}
                hasOlder={current.hasOlder}
                loadOlder={thread.loadOlder}
                loadingOlder={thread.loadingOlder}
              />
              {thread.error && (
                <p
                  role="alert"
                  className="px-4 py-2 text-sm text-red-400 [html[data-theme=light]_&]:text-red-700"
                >
                  {thread.error}
                </p>
              )}
              <Composer
                key={`composer-${current.id}`}
                canSend={current.conversation.can_send}
                busy={thread.sending}
                onSend={thread.send}
              />
            </>
          ) : (
            <div className="flex min-h-0 flex-1 flex-col items-center justify-center p-8 text-center">
              <h2 className="text-xl font-bold">
                {selected
                  ? "Loading conversation..."
                  : "Your next game night starts here"}
              </h2>
              <p className="mt-3 max-w-sm text-sm text-muted">
                {thread.error ||
                  "Choose a conversation or message a friend to get started."}
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
