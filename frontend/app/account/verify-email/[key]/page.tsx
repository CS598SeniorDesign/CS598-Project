"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

type VerificationState =
  "loading" | "ready" | "verifying" | "success" | "error";

function getCookie(name: string): string | null {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.substring(name.length + 1)) : null;
}

export default function VerifyEmailPage() {
  const params = useParams<{ key: string }>();
  const router = useRouter();

  const [status, setStatus] = useState<VerificationState>("loading");
  const [error, setError] = useState("");
  const hasCheckedKey = useRef(false);

  const verificationKey = decodeURIComponent(params.key);

  useEffect(() => {
    if (!verificationKey || hasCheckedKey.current) {
      return;
    }

    hasCheckedKey.current = true;

    const checkVerificationKey = async () => {
      try {
        const response = await fetch("/_allauth/browser/v1/auth/email/verify", {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "X-Email-Verification-Key": verificationKey,
          },
        });

        if (!response.ok) {
          setError(
            "This verification link is invalid or has expired. Please request a new verification email.",
          );
          setStatus("error");
          return;
        }

        setStatus("ready");
      } catch (err) {
        console.error("QuestLog email verification check error:", err);

        setError("Unable to check your verification link. Please try again.");
        setStatus("error");
      }
    };

    void checkVerificationKey();
  }, [verificationKey]);

  const handleVerify = async () => {
    setError("");
    setStatus("verifying");

    try {
      const csrfToken = getCookie("csrf_token");

      if (!csrfToken) {
        throw new Error(
          "Unable to initialize verification security. Please refresh and try again.",
        );
      }

      const response = await fetch("/_allauth/browser/v1/auth/email/verify", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
          "X-Email-Verification-Key": verificationKey,
        },
        body: JSON.stringify({
          key: verificationKey,
        }),
      });

      if (response.ok || response.status === 401) {
        setStatus("success");
        return;
      }

      setError(
        "We could not verify your email. The link may have expired or already been used.",
      );
      setStatus("error");
    } catch (err) {
      console.error("QuestLog email verification error:", err);

      setError(
        err instanceof Error
          ? err.message
          : "Unable to verify your email. Please try again.",
      );
      setStatus("error");
    }
  };

  if (status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <p>Checking your verification link...</p>
      </main>
    );
  }

  if (status === "error") {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <div className="w-full max-w-md text-center">
          <h1 className="mb-4 text-3xl font-bold">Verification Failed</h1>

          <p className="mb-6 text-red-600">{error}</p>

          <button
            type="button"
            onClick={() => router.push("/signup")}
            className="rounded-lg bg-blue-600 px-6 py-3 text-white"
          >
            Back to Sign Up
          </button>
        </div>
      </main>
    );
  }

  if (status === "success") {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <div className="w-full max-w-md text-center">
          <h1 className="mb-4 text-3xl font-bold">Email Verified!</h1>

          <p className="mb-6">
            Your email has been successfully verified. Next, let&apos;s secure
            your QuestLog account.
          </p>

          <button
            type="button"
            onClick={() => router.push("/login?setup=mfa")}
            className="rounded-lg bg-blue-600 px-6 py-3 text-white"
          >
            Continue to MFA Setup
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-md text-center">
        <h1 className="mb-4 text-3xl font-bold">Verify Your Email</h1>

        <p className="mb-6">
          Click below to confirm your email address and continue setting up your
          QuestLog account.
        </p>

        <button
          type="button"
          onClick={handleVerify}
          disabled={status === "verifying"}
          className="rounded-lg bg-blue-600 px-6 py-3 text-white disabled:opacity-50"
        >
          {status === "verifying" ? "Verifying..." : "Verify Email"}
        </button>
      </div>
    </main>
  );
}
