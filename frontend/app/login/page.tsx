"use client";

import { responseCookiesToRequestCookies } from "next/dist/server/web/spec-extension/adapters/request-cookies";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

type AuthResponse = {
  status?: number;
  meta?: {
    is_authenticated?: boolean;
  };
  data?: {
    flows?: Array<{ id: string }>;
  };
};

function getCookie(name: string): string | null {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.substring(name.length + 1)) : null;
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      //browser session and getting the CSRF cookie
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
        if (response.status === 401 || response.status === 400) {
          setError(
            "Unable to sign in. Check your email and passowrd, or verify your account.",
          );
        } else if (response.status === 403) {
          setError(
            "Login was blocked by a security check. Please refresh and try again.",
          );
        } else {
          setError("Something went wrong. Please try again.");
        }
        return;
      }

      if (result.meta?.is_authenticated === true) {
        router.push("/avatar-selection");
        return;
      }

      setError(
        "Your account requires another verification steps before you can proceed.",
      );
    } catch (err) {
      console.error("QuestLog login error:", err);

      setError(
        err instanceof Error
          ? err.message
          : "Could not complete login. Please check your connection and try again.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white">
      <div className="w-full max-w-md bg-gray-900 p-8 rounded-xl">
        <h1 className="text-3xl font-bold mb-6">Login</h1>

        <form
          onSubmit={handleSubmit}
          autoComplete="off"
          className="flex flex-col gap-4"
        >
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
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="p-3 rounded bg-gray-800 border border-gray-700"
            required
            disabled={isLoading}
          />

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
            {isLoading ? "Signing In..." : "Sign In"}
          </button>
        </form>

        <p className="text-sm text-gray-400 mt-6 text-center">
          Don&apos;t have an account?{" "}
          <a href="/signup" className="text-indigo-400 hover:underline">
            Sign Up
          </a>
        </p>
      </div>
    </div>
  );
}
