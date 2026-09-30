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

      if (verificationPending) {
        console.log("Privacy setting:", privacy);
        setSignUpComplete(true);
      }

      if (!response.ok) {
        setError(getSignupErrorMessage(response.status, result));
        return;
      }
      // Note: privacy not sent to auth during account creation, as seen as profile preference.
      console.log("Selected privacy setting:", privacy);
      setSignUpComplete(true);

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
      <div className="min-h-screen flex items-center justify-center bg-black text-white">
        <div className="w-full max-w-md bg-gray-900 p-8 rounded-xl text-center">
          <h1 className="text=3xl font-bold mb-4">Check Your Email</h1>

          <p className="text-gray-300 mb-4">
            Your QuestLog account was created successfully.
          </p>

          <p className="text-gray-400">
            We sent a verification link to{" "}
            <span className="text-white font-medium">{email}</span>. Verify your
            email to continue setting up your account.
          </p>

          <p className="text-sm text-gray-500 mt-6">
            After verifying your email, you can continue with MFA setup.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white">
      <div className="w-full max-w-md bg-gray-900 p-8 rounded-xl">
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

          <select
            value={privacy}
            onChange={(event) => setPrivacy(event.target.value)}
            className="p-3 rounded bg-gray-800 border border-gray-700"
            disabled={isLoading}
          >
            <option value="public">Public</option>
            <option value="friends">Friends Only</option>
            <option value="private">Private</option>
          </select>

          {error && (
            <p role="alert" className="text-sm text-red-400">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="bg-primary py-2 rounded-lg hover:opacity-90 disabled:opacity-60"
          >
            {isLoading ? "Creating Account..." : "Sign Up"}
          </button>
        </form>

        <p className="text-sm text-gray-400 mt-6 text-center">
          Already have an account?{" "}
          <a href="/login" className="text-indigo-400 hover:underline">
            Login
          </a>
        </p>
      </div>
    </div>
  );
}
