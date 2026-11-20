"use client";

import { useState, type FormEvent } from "react";

type AuthResponse = {
  status?: number;
  meta?: {
    is_authenticated?: boolean;
  };
  data?: {
    flows?: Array<{ id: string; is_pending?: boolean }>;
  };
  errors?: Array<{
    message?: string;
    code?: string;
    param?: string;
  }>;
};

function getCookie(name: string): string | null {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.substring(name.length + 1)) : null;
}

function getSignupErrorMessage(status: number, result?: AuthResponse): string {
  const backendMessage = result?.errors?.[0]?.message;

  if (backendMessage) {
    return backendMessage;
  }

  if (status === 400) {
    return "Unable to create your account. Please check your information and then try again.";
  }

  if (status === 403) {
    return "Signup was blocked by a security check. Please refresh and then try agian.";
  }

  if (status == 429) {
    return "Too many signup attempts. Please wait a moment and try again.";
  }

  return "Something went wrong while creating your account. Please try again.";
}

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [privacy, setPrivacy] = useState("public");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [signupComplete, setSignUpComplete] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setError("");
    setIsLoading(true);

    try {
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
          "Unable to initialize signup security. Please refresh and try again.",
        );
      }

      const response = await fetch("/_allauth/browser/v1/auth/signup", {
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

      const verificationPending = result.data?.flows?.some(
        (flow) => flow.id === "verify_email" && flow.is_pending === true,
      );

      // With mandatory email verification, allauth answers a successful signup with 401 and a pending
      // verify_email flow. It answers the same way when the email is already registered (and emails that
      // account's owner instead), so the page never reveals whether an address has an account.
      if (!verificationPending && !response.ok) {
        setError(getSignupErrorMessage(response.status, result));
        return;
      }

      // Note: privacy not sent to auth during account creation, as seen as profile preference.
      console.log("Selected privacy setting:", privacy);
      setSignUpComplete(true);
    } catch (err) {
      console.error("QuestLog signup error:", err);

      setError(
        err instanceof Error
          ? err.message
          : "Could not complete singup. Please check your connection and try again.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (signupComplete) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground p-4">
        <div className="w-full max-w-md rounded-xl border border-border bg-surface p-8 shadow-sm text-center">
          <h1 className="text-3xl font-bold mb-4">Check Your Email</h1>

          <p className="text-subtle mb-4">
            Your QuestLog account was created successfully.
          </p>

          <p className="text-muted">
            We sent a verification link to{" "}
            <span className="text-foreground font-medium">{email}</span>. Verify
            your email to continue setting up your account.
          </p>

          <p className="text-sm text-muted mt-6">
            After verifying your email, you can continue with MFA setup.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground p-4">
      <div className="w-full max-w-md rounded-xl border border-border bg-surface p-8 shadow-sm">
        <h1 className="text-3xl font-bold mb-6">Create Account</h1>

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
            className="rounded-lg border border-border bg-input p-3 text-foreground placeholder:text-muted outline-none focus:border-indigo-500 disabled:opacity-60"
            required
            disabled={isLoading}
          />

          <input
            type="password"
            placeholder="Password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="rounded-lg border border-border bg-input p-3 text-foreground placeholder:text-muted outline-none focus:border-indigo-500 disabled:opacity-60"
            required
            disabled={isLoading}
          />

          <label className="flex flex-col gap-2">
            <span className="sr-only">Privacy</span>
            <select
              value={privacy}
              onChange={(event) => setPrivacy(event.target.value)}
              className="rounded-lg border border-border bg-input p-3 text-foreground placeholder:text-muted outline-none focus:border-indigo-500 disabled:opacity-60"
              disabled={isLoading}
            >
              <option value="public">Public</option>
              <option value="friends">Friends Only</option>
              <option value="private">Private</option>
            </select>
          </label>

          {error && (
            <p
              role="alert"
              className="text-sm text-red-400 [html[data-theme=light]_&]:text-red-700"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="bg-primary py-2 font-medium text-white rounded-lg hover:opacity-90 disabled:opacity-60"
          >
            {isLoading ? "Creating Account..." : "Sign Up"}
          </button>
        </form>

        <p className="text-sm text-muted mt-6 text-center">
          Already have an account?{" "}
          <a href="/login" className="text-link underline">
            Login
          </a>
        </p>
      </div>
    </div>
  );
}
