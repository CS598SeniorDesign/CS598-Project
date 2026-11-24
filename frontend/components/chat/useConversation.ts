"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { chatRequest, mergeMessages, messageOf } from "./api";
import { useChatSummary } from "./ChatProvider";
import type { ChatMessage, Conversation, Results } from "./types";

type Snapshot = {
  id: number;
  conversation: Conversation;
  messages: ChatMessage[];
  hasOlder: boolean;
};

export function useConversation(id: number | null, atBottom: boolean) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const attempt = useRef<{ id: number; body: string; clientId: string } | null>(
    null,
  );
  const sendInFlight = useRef(false);
  const olderInFlight = useRef(false);
  const acknowledged = useRef({ id: 0, message: 0 });
  const { refresh } = useChatSummary();

  const reload = useCallback(
    async (signal?: AbortSignal) => {
      if (id === null) return;
      const [conversation, messages] = await Promise.all([
        chatRequest<Conversation>(`/conversations/${id}/`, { signal }),
        chatRequest<Results<ChatMessage>>(`/conversations/${id}/messages/`, {
          signal,
        }),
      ]);
      if (signal?.aborted) return;
      setSnapshot((old) => ({
        id,
        conversation,
        messages: mergeMessages(
          old?.id === id &&
            old.conversation.language_filter_enabled ===
              conversation.language_filter_enabled
            ? old.messages
            : [],
          messages.results,
        ),
        hasOlder:
          old?.id === id &&
          old.conversation.language_filter_enabled ===
            conversation.language_filter_enabled
            ? old.hasOlder
            : messages.has_more,
      }));
      setError("");
    },
    [id],
  );

  useEffect(() => {
    const controller = new AbortController();
    let pending = false;
    const poll = async () => {
      if (pending || document.visibilityState !== "visible") return;
      pending = true;
      try {
        await reload(controller.signal);
      } catch (caught) {
        if (!controller.signal.aborted) setError(messageOf(caught));
      } finally {
        pending = false;
      }
    };
    void poll();
    const interval = window.setInterval(() => void poll(), 5000);
    const resume = () => void poll();
    document.addEventListener("visibilitychange", resume);
    return () => {
      controller.abort();
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", resume);
    };
  }, [reload]);

  const current = snapshot?.id === id ? snapshot : null;
  const lastId = current?.messages[current.messages.length - 1]?.id ?? 0;
  useEffect(() => {
    async function acknowledge() {
      if (
        !id ||
        !lastId ||
        !atBottom ||
        document.visibilityState !== "visible" ||
        !document.hasFocus()
      )
        return;
      if (
        acknowledged.current.id === id &&
        acknowledged.current.message >= lastId
      )
        return;
      try {
        await chatRequest(`/conversations/${id}/read/`, {
          method: "POST",
          body: { message_id: lastId },
        });
        acknowledged.current = { id, message: lastId };
        await refresh();
      } catch {
        /* A subsequent focus or message poll can retry the acknowledgement. */
      }
    }
    void acknowledge();
    const resume = () => void acknowledge();
    window.addEventListener("focus", resume);
    document.addEventListener("visibilitychange", resume);
    return () => {
      window.removeEventListener("focus", resume);
      document.removeEventListener("visibilitychange", resume);
    };
  }, [id, lastId, atBottom, refresh]);

  async function send(body: string): Promise<boolean> {
    if (!id || sendInFlight.current) return false;
    sendInFlight.current = true;
    setSending(true);
    setError("");
    const previous = attempt.current;
    const clientId =
      previous?.id === id && previous.body === body
        ? previous.clientId
        : crypto.randomUUID();
    attempt.current = { id, body, clientId };
    try {
      const message = await chatRequest<ChatMessage>(
        `/conversations/${id}/messages/`,
        { method: "POST", body: { body, client_id: clientId } },
      );
      setSnapshot((old) =>
        old?.id === id
          ? { ...old, messages: mergeMessages(old.messages, [message]) }
          : old,
      );
      attempt.current = null;
      await refresh();
      return true;
    } catch (caught) {
      setError(messageOf(caught));
      return false;
    } finally {
      sendInFlight.current = false;
      setSending(false);
    }
  }

  async function loadOlder() {
    const first = current?.messages[0];
    if (!id || !first || olderInFlight.current) return;
    olderInFlight.current = true;
    setLoadingOlder(true);
    try {
      const result = await chatRequest<Results<ChatMessage>>(
        `/conversations/${id}/messages/?before=${first.id}`,
      );
      setSnapshot((old) =>
        old?.id === id
          ? {
              ...old,
              messages: mergeMessages(result.results, old.messages),
              hasOlder: result.has_more,
            }
          : old,
      );
    } catch (caught) {
      setError(messageOf(caught));
    } finally {
      olderInFlight.current = false;
      setLoadingOlder(false);
    }
  }

  return { current, error, sending, send, reload, loadOlder, loadingOlder };
}
