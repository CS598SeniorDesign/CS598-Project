"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

type AuthResponse = {
  status?: number;
  meta?: {
    is_authenticated?: boolean;
  };
  data?: {
    user?: {
      email?: string;
    };
    flows?: Array<{ id: string; is_pending?: boolean }>;
  };
};

function hasPendingMfa(result: AuthResponse): boolean {
  return (
    result.data?.flows?.some(
      (flow) => flow.id === "mfa_authenticate" && flow.is_pending === true,
    ) ?? false
  );
}

function getCookie(name: string): string | null {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.substring(name.length + 1)) : null;
}

function getLoginErrorMessage(status: number): string {
  if (status === 401 || status === 400) {
    return "Unable to sign in. Check your email and password, or verify your account.";
  }

  if (status === 403) {
    return "Login was blocked by a security check. Please refresh and try again.";
  }

  if (status === 429) {
    return "Too many attempts. Please wait a little before trying again.";
  }

  return "Something went wrong. Please try again.";
}

function getLoginDestination(): string {
  const searchParams = new URLSearchParams(window.location.search);

  return searchParams.get("setup") === "mfa"
    ? "/mfa-setup"
    : "/avatar-selection";
}

async function getSession(): Promise<AuthResponse> {
  const response = await fetch("/_allauth/browser/v1/auth/session", {
    credentials: "same-origin",
    cache: "no-store",
  });

  if (!response.ok && response.status !== 401) {
    throw new Error("Unable to connect to the server. Please try again.");
  }

  return (await response.json()) as AuthResponse;
}

function checkExistingSession(
  session: AuthResponse,
  email: string,
): AuthResponse | null {
  if (!session.meta?.is_authenticated) {
    return null;
  }

  const activeEmail = session.data?.user?.email;

  if (activeEmail?.toLowerCase() !== email.trim().toLowerCase()) {
    throw new Error(
      "Another account is already signed in. Sign out of QuestLog first, or use a private window.",
    );
  }

  return session;
}

async function postAuth(
  path: string,
  body: Record<string, string>,
): Promise<{ response: Response; result: AuthResponse }> {
  const csrfToken = getCookie("csrf_token");

  if (!csrfToken) {
    throw new Error(
      "Unable to initialize login security. Please refresh and try again.",
    );
  }

  const response = await fetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify(body),
  });

  const result: AuthResponse = await response.json();

  return { response, result };
}

async function loginUser(
  email: string,
  password: string,
): Promise<AuthResponse> {
  const session = await getSession();
  const existingSession = checkExistingSession(session, email);

  if (existingSession) {
    return existingSession;
  }

  const { response, result } = await postAuth(
    "/_allauth/browser/v1/auth/login",
    {
      email: email.trim(),
      password,
    },
  );

  if (response.ok || (response.status === 401 && hasPendingMfa(result))) {
    return result;
  }

  if (response.status === 409) {
    const latestSession = await getSession();
    const authenticatedSession = checkExistingSession(latestSession, email);

    if (authenticatedSession) {
      return authenticatedSession;
    }

    throw new Error(
      "Your login session changed. Refresh the page and try again.",
    );
  }

  throw new Error(getLoginErrorMessage(response.status));
}

async function verifyMfa(code: string): Promise<AuthResponse> {
  await getSession();

  const { response, result } = await postAuth(
    "/_allauth/browser/v1/auth/2fa/authenticate",
    { code },
  );

  if (response.ok) {
    return result;
  }

  if (response.status === 400 || response.status === 401) {
    throw new Error(
      "The code was not accepted or your login expired. Try the latest code, or go back and sign in again.",
    );
  }

  throw new Error(getLoginErrorMessage(response.status));
}

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [requiresMfaCode, setRequiresMfaCode] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (isLoading) {
      return;
    }

    setError("");
    setIsLoading(true);

    try {
      const result = requiresMfaCode
        ? await verifyMfa(mfaCode)
        : await loginUser(email, password);

      if (result.meta?.is_authenticated === true) {
        setPassword("");
        setMfaCode("");
        router.replace(getLoginDestination());
        return;
      }

      if (hasPendingMfa(result)) {
        setRequiresMfaCode(true);
        setPassword("");
        setMfaCode("");
        return;
      }

      setError(
        "Another verification step is required. Check that your email is verified before signing in.",
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not complete login. Please try again.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleBack = () => {
    setRequiresMfaCode(false);
    setMfaCode("");
    setPassword("");
    setError("");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white">
      <div className="w-full max-w-md bg-gray-900 p-8 rounded-xl">
        <h1 className="text-3xl font-bold mb-6">
          {requiresMfaCode ? "Verify Your Identity" : "Login"}
        </h1>

        {requiresMfaCode && (
          <p className="text-gray-400 mb-6">
            Enter the code from your authenticator app to finish signing in.
          </p>
        )}

        <form
          onSubmit={handleSubmit}
          autoComplete="off"
          className="flex flex-col gap-4"
        >
          {requiresMfaCode ? (
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              aria-label="Authenticator code"
              placeholder="6-digit authenticator code"
              value={mfaCode}
              onChange={(event) =>
                setMfaCode(event.target.value.replace(/\D/g, "").slice(0, 6))
              }
              className="p-3 rounded bg-gray-800 border border-gray-700"
              maxLength={6}
              pattern="[0-9]{6}"
              required
              disabled={isLoading}
            />
          ) : (
            <>
              <input
                type="email"
                aria-label="Email"
                placeholder="Email"
                autoComplete="off"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="p-3 rounded bg-gray-800 border border-gray-700"
                required
                disabled={isLoading}
              />

              <input
                type="password"
                aria-label="Password"
                placeholder="Password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="p-3 rounded bg-gray-800 border border-gray-700"
                required
                disabled={isLoading}
              />
            </>
          )}

          {error && (
            <p role="alert" className="text-sm text-red-400">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="bg-primary py-2 rounded-lg hover:opacity-90"
          >
            {isLoading
              ? "Please wait..."
              : requiresMfaCode
                ? "Verify Code"
                : "Sign In"}
          </button>

          {requiresMfaCode && (
            <button
              type="button"
              onClick={handleBack}
              disabled={isLoading}
              className="text-sm text-gray-400 hover:text-white"
            >
              Back to Login
            </button>
          )}
        </form>

        {!requiresMfaCode && (
          <p className="text-sm text-gray-400 mt-6 text-center">
            Don&apos;t have an account?{" "}
            <a href="/signup" className="text-indigo-400 hover:underline">
              Sign Up
            </a>
          </p>
        )}
      </div>
    </div>
  );
}
