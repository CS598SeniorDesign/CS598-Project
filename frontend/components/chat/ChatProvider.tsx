"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { ChatError, chatRequest } from "./api";
import type { ChatSummary } from "./types";

const ChatContext = createContext({
  unread: 0,
  userId: null as string | null,
  ready: false,
  refresh: async () => {},
});
export function useChatSummary() {
  return useContext(ChatContext);
}

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [summary, setSummary] = useState<ChatSummary | null>(null);
  const [notice, setNotice] = useState(false);
  const [ready, setReady] = useState(false);
  const actor = useRef<string | null>(null);
  const previous = useRef<number | null>(null);
  const heartbeatAt = useRef(0);
  const pending = useRef(false);

  const acceptSummary = useCallback(async (next: ChatSummary) => {
    if (actor.current !== next.user_id) {
      actor.current = next.user_id;
      previous.current = null;
      setNotice(false);
    }
    setReady(true);
    if (
      previous.current !== null &&
      next.unread_count > previous.current &&
      next.message_notifications
    )
      setNotice(true);
    if (!next.message_notifications || next.unread_count === 0)
      setNotice(false);
    previous.current = next.unread_count;
    setSummary(next);
    if (document.hasFocus() && Date.now() - heartbeatAt.current > 30000) {
      heartbeatAt.current = Date.now();
      await chatRequest("/presence/", { method: "POST" });
    }
  }, []);

  const handleFailure = useCallback((caught: unknown) => {
    setReady(true);
    if (
      caught instanceof ChatError &&
      (caught.status === 401 || caught.status === 403)
    ) {
      previous.current = null;
      actor.current = null;
      setSummary(null);
      setNotice(false);
    }
  }, []);

  const refresh = useCallback((): Promise<void> => {
    if (pending.current || document.visibilityState !== "visible")
      return Promise.resolve();
    pending.current = true;
    return chatRequest<ChatSummary>("/summary/")
      .then(acceptSummary)
      .catch(handleFailure)
      .finally(() => {
        pending.current = false;
      });
  }, [acceptSummary, handleFailure]);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(), 15000);
    const resume = () => void refresh();
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("focus", resume);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", resume);
      window.removeEventListener("focus", resume);
    };
  }, [refresh, pathname]);

  return (
    <ChatContext.Provider
      value={{
        unread: summary?.unread_count ?? 0,
        userId: summary?.user_id ?? null,
        ready,
        refresh,
      }}
    >
      {children}
      {notice && pathname !== "/chat" && (
        <aside
          role="status"
          className="fixed bottom-5 right-5 z-50 max-w-xs rounded-2xl border border-border bg-surface p-4 text-foreground shadow-xl"
        >
          <Link
            href="/chat"
            onClick={() => setNotice(false)}
            className="font-semibold text-link"
          >
            You have new Weeple Chat messages
          </Link>
          <button
            type="button"
            onClick={() => setNotice(false)}
            aria-label="Dismiss message notification"
            className="ml-3 rounded px-2 py-1 text-muted hover:bg-surface-hover"
          >
            ×
          </button>
        </aside>
      )}
    </ChatContext.Provider>
  );
}

export function ChatNavLink() {
  const { unread } = useChatSummary();
  return (
    <Link
      href="/chat"
      className="inline-flex items-center gap-2 rounded-lg px-3 py-2 font-semibold text-foreground hover:bg-surface-hover"
      aria-label={`Chat${unread ? `, ${unread} unread messages` : ""}`}
    >
      Chat
      {unread > 0 && (
        <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-xs text-white">
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </Link>
  );
}
