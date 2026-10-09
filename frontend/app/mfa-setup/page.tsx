"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

type TOTPResponse = {
  status?: number;
  data?: {
    flows?: Array<{ id?: string }>;
  };
  meta?: {
    secret?: string;
    totp_url?: string;
    is_authenticated?: boolean;
  };
};

type RecoveryCodesResponse = {
  data?: {
    unused_codes?: string[];
  };
};

type TOTPSetupResult =
  | { action: "setup"; secret: string; totpUrl: string }
  | { action: "login" }
  | { action: "configured" }
  | { action: "error" };

type MFAActivationResult =
  "success" | "invalid-code" | "reauthenticate" | "login" | "error";

function getCookie(name: string): string | null {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.substring(name.length + 1)) : null;
}

async function getTOTPSetup(): Promise<TOTPSetupResult> {
  const response = await fetch(
    "/_allauth/browser/v1/account/authenticators/totp",
    {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
    },
  );

  const result: TOTPResponse = await response.json();

  if (response.status === 404 && result.meta?.secret && result.meta?.totp_url) {
    return {
      action: "setup",
      secret: result.meta.secret,
      totpUrl: result.meta.totp_url,
    };
  }

  if (response.status === 401 && result.meta?.is_authenticated !== true) {
    return { action: "login" };
  }

  if (response.ok) {
    return { action: "configured" };
  }

  return { action: "error" };
}

async function reauthenticatePassword(password: string): Promise<Response> {
  const csrfToken = getCookie("csrf_token");

  if (!csrfToken) {
    throw new Error(
      "Unable to initialize account security. Please refresh and try again.",
    );
  }

  return fetch("/_allauth/browser/v1/auth/reauthenticate", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({ password }),
  });
}

async function getUnauthorizedMFAResult(
  response: Response,
): Promise<MFAActivationResult> {
  let result: TOTPResponse | null = null;

  try {
    result = await response.json();
  } catch {
    return "error";
  }

  const requiresReauthentication = result?.data?.flows?.some(
    (flow) => flow.id === "reauthenticate",
  );

  if (requiresReauthentication) {
    return "reauthenticate";
  }

  if (result?.meta?.is_authenticated !== true) {
    return "login";
  }

  return "error";
}

async function activateTOTP(code: string): Promise<MFAActivationResult> {
  const csrfToken = getCookie("csrf_token");

  if (!csrfToken) {
    throw new Error(
      "Unable to initialize MFA security. Please refresh and try again.",
    );
  }

  const response = await fetch(
    "/_allauth/browser/v1/account/authenticators/totp",
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ code }),
    },
  );

  if (response.ok) {
    return "success";
  }

  if (response.status === 400) {
    return "invalid-code";
  }

  if (response.status === 401) {
    return getUnauthorizedMFAResult(response);
  }

  return "error";
}

async function getRecoveryCodes(): Promise<string[]> {
  const response = await fetch(
    "/_allauth/browser/v1/account/authenticators/recovery-codes",
    {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error("Unable to load recovery codes. Please try again.");
  }

  const result: RecoveryCodesResponse = await response.json();
  const codes = result.data?.unused_codes;

  if (
    !Array.isArray(codes) ||
    codes.length === 0 ||
    !codes.every((code) => typeof code === "string")
  ) {
    throw new Error(
      "No recovery codes were returned. Please try again or contact support.",
    );
  }

  return codes;
}

function MFALoadingScreen() {
  return (
    <main className="min-h-screen bg-gray-900 text-white">
      <div className="flex min-h-[calc(100vh-80px)] items-center justify-center px-6">
        <p className="text-gray-400">Loading MFA setup...</p>
      </div>
    </main>
  );
}

type RecoveryCodesScreenProps = {
  codes: string[] | null;
  error: string;
  isLoading: boolean;
  copied: boolean;
  saved: boolean;
  onRetry: () => void;
  onCopy: () => void;
  onSavedChange: (saved: boolean) => void;
  onContinue: () => void;
};

function RecoveryCodesScreen({
  codes,
  error,
  isLoading,
  copied,
  saved,
  onRetry,
  onCopy,
  onSavedChange,
  onContinue,
}: RecoveryCodesScreenProps) {
  return (
    <main className="min-h-screen bg-gray-900 text-white">
      <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col justify-center px-6 py-12">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white">
            MFA Enabled Successfully!
          </h1>

          <p className="mt-3 text-gray-400">
            Your QuestLog account is now protected with two-factor
            authentication.
          </p>
        </div>

        <div className="mt-8 rounded-xl border border-amber-700 bg-amber-950/30 p-5">
          <h2 className="font-semibold text-amber-200">
            Important: Save Your Recovery Codes
          </h2>

          <p className="mt-2 text-sm text-amber-100/80">
            Recovery codes can help you sign in if you lose access to your
            authenticator app. Each code can only be used once. Keep them in a
            safe, private place, such as a password manager.
          </p>

          <p className="mt-2 text-sm text-amber-100/80">
            Do not share these codes with anyone.
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="mt-6 rounded-lg border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-300"
          >
            {error}
          </div>
        )}

        {codes ? (
          <>
            <div className="mt-6 rounded-xl border border-gray-700 bg-black/30 p-6">
              <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold">Your Recovery Codes</h2>

                <button
                  type="button"
                  onClick={onCopy}
                  className="rounded-lg border border-gray-600 px-4 py-2 text-sm font-medium transition hover:bg-gray-800"
                >
                  {copied ? "✓ Copied!" : "Copy All Codes"}
                </button>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {codes.map((code, index) => (
                  <div
                    key={index}
                    className="rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-center"
                  >
                    <code className="break-all font-mono text-sm text-gray-100">
                      {code}
                    </code>
                  </div>
                ))}
              </div>
            </div>

            <label className="mt-7 flex cursor-pointer items-start gap-3 rounded-lg border border-gray-700 p-4">
              <input
                type="checkbox"
                checked={saved}
                onChange={(event) => onSavedChange(event.target.checked)}
                className="mt-1 h-4 w-4 accent-indigo-600"
              />

              <span className="text-sm text-gray-300">
                I have saved my recovery codes in a secure location and
                understand that I may need them if I lose access to my
                authenticator app.
              </span>
            </label>

            <button
              type="button"
              onClick={onContinue}
              disabled={!saved}
              className="mt-6 rounded-lg bg-indigo-600 px-7 py-3 font-medium transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Continue to Avatar Selection
            </button>
          </>
        ) : (
          <div className="mt-8 text-center">
            <p className="text-gray-400">
              {isLoading
                ? "Loading your recovery codes..."
                : "Your MFA is enabled, but your recovery codes could not be displayed."}
            </p>

            {!isLoading && (
              <button
                type="button"
                onClick={onRetry}
                className="mt-5 rounded-lg bg-indigo-600 px-6 py-3 font-medium transition hover:bg-indigo-500"
              >
                Retry Loading Recovery Codes
              </button>
            )}
          </div>
        )}
      </div>
    </main>
  );
}

// eslint-disable-next-line complexity
export default function MFASetup() {
  const router = useRouter();

  const [secret, setSecret] = useState("");
  const [totpUrl, setTotpUrl] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isEnabling, setIsEnabling] = useState(false);

  const [passwordConfirmed, setPasswordConfirmed] = useState(false);
  const [copied, setCopied] = useState(false);

  const [mfaActivated, setMfaActivated] = useState(false);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [recoveryCodesCopied, setRecoveryCodesCopied] = useState(false);
  const [recoveryCodesSaved, setRecoveryCodesSaved] = useState(false);
  const [isLoadingRecoveryCodes, setIsLoadingRecoveryCodes] = useState(false);

  useEffect(() => {
    const loadTOTPSetup = async () => {
      try {
        const result = await getTOTPSetup();

        if (result.action === "setup") {
          setSecret(result.secret);
          setTotpUrl(result.totpUrl);
          return;
        }

        if (result.action === "login") {
          router.push("/login?setup=mfa");
          return;
        }

        if (result.action === "configured") {
          router.push("/avatar-selection");
          return;
        }

        setError("Unable to load MFA setup. Please try again.");
      } catch (err) {
        console.error("QuestLog MFA setup error:", err);
        setError("Unable to load MFA setup. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    void loadTOTPSetup();
  }, [router]);

  const loadRecoveryCodes = async () => {
    setError("");
    setIsLoadingRecoveryCodes(true);

    try {
      const codes = await getRecoveryCodes();
      setRecoveryCodes(codes);
    } catch (err) {
      console.error("QuestLog recovery codes error:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load recovery codes. Please try again.",
      );
    } finally {
      setIsLoadingRecoveryCodes(false);
    }
  };

  const handleCopySecret = async () => {
    if (!secret) {
      return;
    }

    try {
      await navigator.clipboard.writeText(secret);
      setCopied(true);

      window.setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch (err) {
      console.error("Unable to copy MFA setup key:", err);
      setError("Unable to copy the setup key. Please copy it manually.");
    }
  };

  const handleCopyRecoveryCodes = async () => {
    if (!recoveryCodes) {
      return;
    }

    try {
      await navigator.clipboard.writeText(recoveryCodes.join("\n"));
      setRecoveryCodesCopied(true);
      setError("");
    } catch (err) {
      console.error("Unable to copy recovery codes:", err);
      setError("Unable to copy recovery codes. Please save them manually.");
    }
  };

  const handleReauthenticate = async () => {
    setError("");

    if (!password) {
      setError("Enter your password to continue.");
      return;
    }

    setIsEnabling(true);

    try {
      const response = await reauthenticatePassword(password);

      if (response.status === 400) {
        setError(
          "That password was not accepted. Please check your password and try again.",
        );
        return;
      }

      if (response.status === 401) {
        setError("Your session has expired. Please log in again.");
        return;
      }

      if (!response.ok) {
        setError("Unable to verify your password. Please try again.");
        return;
      }

      setPasswordConfirmed(true);
      setPassword("");
      setCode("");
      setError("");
    } catch (err) {
      console.error("QuestLog reauthentication error:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to verify your password. Please try again.",
      );
    } finally {
      setIsEnabling(false);
    }
  };

  const handleEnableMFA = async () => {
    setError("");

    if (!/^\d{6}$/.test(code)) {
      setError(
        "Enter the six-digit code currently shown in your authenticator app.",
      );
      return;
    }

    setIsEnabling(true);

    try {
      const result = await activateTOTP(code);

      if (result === "success") {
        setMfaActivated(true);
        setSecret("");
        setTotpUrl("");
        setCode("");
        setPassword("");
        await loadRecoveryCodes();
        return;
      }

      if (result === "invalid-code") {
        setCode("");
        setError(
          "That verification code is invalid or has expired. Enter the current code from your authenticator app.",
        );
        return;
      }

      if (result === "reauthenticate") {
        setPasswordConfirmed(false);
        setPassword("");
        setCode("");
        setError("Please confirm your password again before enabling MFA.");
        return;
      }

      if (result === "login") {
        router.push("/login?setup=mfa");
        return;
      }

      setError("Unable to enable MFA. Please try again.");
    } catch (err) {
      console.error("QuestLog MFA activation error:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to enable MFA. Please try again.",
      );
    } finally {
      setIsEnabling(false);
    }
  };

  const handleSkip = () => {
    router.push("/avatar-selection");
  };

  const handleBack = () => {
    setPasswordConfirmed(false);
    setPassword("");
    setCode("");
    setError("");
  };

  if (isLoading) {
    return <MFALoadingScreen />;
  }

  if (mfaActivated) {
    return (
      <RecoveryCodesScreen
        codes={recoveryCodes}
        error={error}
        isLoading={isLoadingRecoveryCodes}
        copied={recoveryCodesCopied}
        saved={recoveryCodesSaved}
        onRetry={() => void loadRecoveryCodes()}
        onCopy={() => void handleCopyRecoveryCodes()}
        onSavedChange={setRecoveryCodesSaved}
        onContinue={() => router.push("/avatar-selection")}
      />
    );
  }

  return (
    <main className="min-h-screen bg-gray-900 text-white">
      <div className="mx-auto flex min-h-[calc(100vh-80px)] w-full max-w-3xl flex-col justify-center px-6 py-12 sm:px-10">
        <div className="text-center">
          <h1 className="text-3xl font-bold sm:text-4xl">
            Secure Your Account
          </h1>

          <p className="mx-auto mt-3 max-w-xl text-gray-400">
            Scan this QR code with your authenticator app to add QuestLog to
            your account.
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="mx-auto mt-6 w-full max-w-xl rounded-lg border border-red-800 bg-red-950/40 px-4 py-3 text-center text-sm text-red-300"
          >
            {error}
          </div>
        )}

        {totpUrl && (
          <div className="mt-8 flex justify-center">
            <div className="rounded-xl bg-white p-4">
              <QRCodeSVG value={totpUrl} size={190} />
            </div>
          </div>
        )}

        {secret && (
          <div className="mx-auto mt-7 w-full max-w-xl">
            <p className="mb-3 text-center text-sm text-gray-400">
              Can&apos;t scan the QR code? Enter this setup key manually:
            </p>

            <div className="flex items-center gap-3 rounded-xl border border-gray-700 bg-black/30 p-3">
              <code className="min-w-0 flex-1 break-all text-sm text-gray-200 sm:text-base">
                {secret}
              </code>

              <button
                type="button"
                onClick={() => void handleCopySecret()}
                className="shrink-0 rounded-lg border border-gray-600 px-4 py-2 text-sm font-medium text-gray-200 transition hover:border-gray-400 hover:bg-gray-800"
              >
                {copied ? "✓ Copied!" : "Copy"}
              </button>
            </div>
          </div>
        )}

        <div className="mx-auto mt-9 w-full max-w-xl border-t border-gray-800 pt-8">
          {!passwordConfirmed ? (
            <>
              <div className="text-center">
                <h2 className="text-xl font-semibold">Confirm Your Password</h2>

                <p className="mt-2 text-sm text-gray-400">
                  For your security, confirm your QuestLog password before
                  enabling MFA.
                </p>
              </div>

              <div className="mt-6">
                <label
                  htmlFor="password"
                  className="mb-2 block text-sm font-medium text-gray-300"
                >
                  Password
                </label>

                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  disabled={isEnabling}
                  onChange={(event) => setPassword(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && password && !isEnabling) {
                      void handleReauthenticate();
                    }
                  }}
                  placeholder="Enter your password"
                  className="w-full rounded-lg border border-gray-700 bg-black/30 px-4 py-3 outline-none transition focus:border-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>

              <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={() => void handleReauthenticate()}
                  disabled={!password || isEnabling}
                  className="rounded-lg bg-indigo-600 px-7 py-3 font-medium transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isEnabling ? "Verifying..." : "Continue"}
                </button>

                <button
                  type="button"
                  onClick={handleSkip}
                  disabled={isEnabling}
                  className="rounded-lg border border-gray-600 px-7 py-3 font-medium text-gray-200 transition hover:border-gray-400 hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Skip
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="text-center">
                <h2 className="text-xl font-semibold">
                  Enter Verification Code
                </h2>

                <p className="mt-2 text-sm text-gray-400">
                  Enter the current six-digit code shown in your authenticator
                  app.
                </p>
              </div>

              <div className="mt-6">
                <label
                  htmlFor="verification-code"
                  className="mb-2 block text-center text-sm font-medium text-gray-300"
                >
                  Verification Code
                </label>

                <input
                  id="verification-code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  value={code}
                  disabled={isEnabling}
                  onChange={(event) =>
                    setCode(event.target.value.replace(/\D/g, ""))
                  }
                  onKeyDown={(event) => {
                    if (
                      event.key === "Enter" &&
                      code.length === 6 &&
                      !isEnabling
                    ) {
                      void handleEnableMFA();
                    }
                  }}
                  placeholder="000000"
                  className="mx-auto block w-full max-w-xs rounded-lg border border-gray-700 bg-black/30 px-4 py-3 text-center text-2xl tracking-[0.35em] outline-none transition focus:border-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>

              <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={() => void handleEnableMFA()}
                  disabled={code.length !== 6 || isEnabling}
                  className="rounded-lg bg-indigo-600 px-7 py-3 font-medium transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isEnabling ? "Enabling..." : "Enable MFA"}
                </button>

                <button
                  type="button"
                  onClick={handleBack}
                  disabled={isEnabling}
                  className="rounded-lg border border-gray-600 px-7 py-3 font-medium text-gray-200 transition hover:border-gray-400 hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Back
                </button>
              </div>
            </>
          )}

          <p className="mt-6 text-center text-xs text-gray-500">
            You can enable MFA later in Settings.
          </p>
        </div>
      </div>
    </main>
  );
}
