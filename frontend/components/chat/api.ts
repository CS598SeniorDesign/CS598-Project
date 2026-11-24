export class ChatError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

function csrfToken() {
  const item = document.cookie
    .split("; ")
    .find((value) => value.startsWith("csrf_token="));
  return item ? decodeURIComponent(item.slice("csrf_token=".length)) : "";
}

function errorMessage(value: unknown) {
  if (!value || typeof value !== "object")
    return "Unable to complete this request. Please try again.";
  const messages = Object.values(value)
    .flat()
    .filter((item) => typeof item === "string");
  return (
    messages.join(" ") || "Unable to complete this request. Please try again."
  );
}

async function securityHeaders(
  method: string,
): Promise<Record<string, string>> {
  if (method === "GET") return {};
  if (!csrfToken())
    await fetch("/csrf/", { credentials: "same-origin", cache: "no-store" });
  const token = csrfToken();
  if (!token)
    throw new ChatError(
      "Refresh the page to initialize your security token.",
      403,
    );
  return { "X-CSRFToken": token };
}

export async function chatRequest<T>(
  path: string,
  options: {
    method?: "GET" | "POST" | "PATCH" | "DELETE";
    body?: object;
    signal?: AbortSignal;
  } = {},
): Promise<T> {
  const method = options.method ?? "GET";
  const security = await securityHeaders(method);
  const response = await fetch(`/api/v1/chat${path}`, {
    method,
    credentials: "same-origin",
    cache: "no-store",
    signal: options.signal,
    headers: {
      Accept: "application/json",
      ...security,
      ...(options.body ? { "Content-Type": "application/json" } : {}),
    },
    ...(options.body ? { body: JSON.stringify(options.body) } : {}),
  });
  if (response.status === 204) return undefined as T;
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ChatError(errorMessage(payload), response.status);
  return payload as T;
}

export function messageOf(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Unable to load chat. Please try again.";
}
export function mergeMessages<T extends { id: number }>(old: T[], next: T[]) {
  const values = new Map(old.map((item) => [item.id, item]));
  next.forEach((item) => values.set(item.id, item));
  return [...values.values()].sort((a, b) => a.id - b.id);
}
export function mergeConversations<
  T extends { id: number; updated_at: string },
>(old: T[], next: T[]) {
  return mergeMessages(old, next).sort(
    (a, b) => b.updated_at.localeCompare(a.updated_at) || b.id - a.id,
  );
}
