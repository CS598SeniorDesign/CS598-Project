/**
 * Shared helpers for calling the Django API through the same-origin proxy.
 *
 * Requests send the session cookie, and writes send the CSRF token allauth
 * keeps in the csrf_token cookie.
 */

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;

  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));

  return cookie
    ? decodeURIComponent(cookie.split("=").slice(1).join("="))
    : null;
}

export function getCsrfToken(): string | null {
  return getCookie("csrf_token") ?? getCookie("csrftoken");
}

/**
 * Collect the messages from a DRF error body: `{"detail": "..."}` or
 * `{"field": ["...", ...], "non_field_errors": [...]}`.
 */
export function drfMessages(body: unknown): string[] {
  if (typeof body === "string") return [body];
  if (Array.isArray(body)) return body.flatMap(drfMessages);
  if (body && typeof body === "object") {
    return Object.values(body as Record<string, unknown>).flatMap(drfMessages);
  }
  return [];
}

/** Build a query string, leaving out empty values. */
export function toQueryString(
  params: Record<string, string | number | boolean | null | undefined>,
): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") continue;
    search.set(key, String(value));
  }

  const text = search.toString();
  return text ? `?${text}` : "";
}

/**
 * Send a request and parse the JSON response.
 *
 * @param describeError - Turns a failed response into a user-facing message.
 * @throws ApiError with that message when the response is not OK.
 */
export async function apiRequest<T>(
  url: string,
  init: RequestInit = {},
  describeError: (status: number, body: unknown) => string = (_, body) =>
    drfMessages(body).join(" ") || "Something went wrong. Please try again.",
): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };

  if (method !== "GET") {
    const csrfToken = getCsrfToken();
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
    if (init.body) headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    ...init,
    method,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      describeError(response.status, body),
      response.status,
      body,
    );
  }

  return body as T;
}
