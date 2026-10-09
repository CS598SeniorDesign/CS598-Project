"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

type AuthResponse = {
  status?: number;
  meta?: {
    is_authenticated?: boolean;
  };
  data?: {
    flows?: Array<{ id: string; is_pending?: boolean }>;
  };
};

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

  return "Something went wrong. Please try again.";
}

function getLoginDestination(): string {
  const searchParams = new URLSearchParams(window.location.search);

  return searchParams.get("setup") === "mfa"
    ? "/mfa-setup"
    : "/avatar-selection";
}

async function loginUser(
  email: string,
  password: string,
): Promise<AuthResponse> {
  const sessionResponse = await fetch("/_allauth/browser/v1/auth/session", {
    credentials: "same-origin",
    cache: "no-store",
  });

  if (!sessionResponse.ok && sessionResponse.status !== 401) {
    throw new Error("Unable to connect to the server. Please try again.");
  }

  const csrfToken = getCookie("csrf_token");

  if (!csrfToken) {
    throw new Error(
      "Unable to initialize the login security. Please refresh and try again!",
    );
  }

  const response = await fetch("/_allauth/browser/v1/auth/login", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({
      email: email.trim(),
      password,
    }),
  });

  const result: AuthResponse = await response.json();

  if (!response.ok) {
    throw new Error(getLoginErrorMessage(response.status));
  }

  return result;
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
    setError("");
    setIsLoading(true);

    try {
      const result = await loginUser(email, password);

      if (result.meta?.is_authenticated === true) {
        router.push(getLoginDestination());
        return;
      }

      setError(
        "Your account requires another verification step before you can proceed.",
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
