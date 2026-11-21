"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import {
  Settings,
  Shield,
  UserRound,
  LockKeyhole,
  Mail,
  Camera,
  Eye,
  EyeOff,
} from "lucide-react";

import { useTheme } from "@/components/theme/ThemeProvider";

type SettingsTab = "account" | "appearance" | "security" | "privacy";
type PrivacyLevel = "PUBLIC" | "FRIENDS" | "PRIVATE";

type UserProfile = {
  user_id: string;
  display_name: string;
  bio: string;
  avatar: string;
  privacy_level: PrivacyLevel;
  bgg_username: string;
};

type EmailAddress = {
  email: string;
  primary: boolean;
  verified: boolean;
};

const privacyOptions: {
  value: PrivacyLevel;
  label: string;
  description: string;
}[] = [
  {
    value: "PUBLIC",
    label: "Public",
    description: "Use the public profile visibility setting.",
  },
  {
    value: "FRIENDS",
    label: "Friends Only",
    description: "Use the friends-only profile visibility setting.",
  },
  {
    value: "PRIVATE",
    label: "Private",
    description: "Use the private profile visibility setting.",
  },
];

function getCsrfToken(): string {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith("csrf_token="));

  return cookie
    ? decodeURIComponent(cookie.substring("csrf_token=".length))
    : "";
}

async function fetchProfile(signal: AbortSignal): Promise<UserProfile> {
  const response = await fetch("/api/v1/profile/", {
    credentials: "include",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error(
      response.status === 401 || response.status === 403
        ? "Please log in to view your settings."
        : "Unable to load your account settings.",
    );
  }

  return (await response.json()) as UserProfile;
}

function getEmailCandidates(result: unknown): unknown[] {
  const response = result as {
    data?:
      | {
          emailaddresses?: unknown[];
          emails?: unknown[];
        }
      | unknown[];
  };

  const data = response?.data;

  if (Array.isArray(data)) {
    return data;
  }

  const candidates = data?.emailaddresses ?? data?.emails;

  if (Array.isArray(candidates)) {
    return candidates;
  }

  throw new Error("Email information was not returned.");
}

function parseEmailAddresses(items: unknown[]): EmailAddress[] {
  return items
    .filter(
      (item): item is EmailAddress =>
        typeof item === "object" &&
        item !== null &&
        "email" in item &&
        typeof item.email === "string",
    )
    .map((item) => ({
      email: item.email,
      primary: item.primary === true,
      verified: item.verified === true,
    }));
}

async function fetchEmails(signal: AbortSignal): Promise<EmailAddress[]> {
  const response = await fetch("/_allauth/browser/v1/account/email", {
    credentials: "include",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error("Unable to retrieve account email addresses.");
  }

  const result: unknown = await response.json();
  const candidates = getEmailCandidates(result);

  return parseEmailAddresses(candidates);
}

async function savePrivacyLevel(
  privacyLevel: PrivacyLevel,
): Promise<UserProfile> {
  const csrfToken = getCsrfToken();

  const response = await fetch("/api/v1/profile/", {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
    },
    body: JSON.stringify({
      privacy_level: privacyLevel,
    }),
  });

  if (!response.ok) {
    throw new Error(
      response.status === 401 || response.status === 403
        ? "Unable to save privacy settings. Check your session and CSRF configuration."
        : "Unable to save your privacy settings.",
    );
  }

  return (await response.json()) as UserProfile;
}

function validatePasswordChange(
  currentPassword: string,
  newPassword: string,
  confirmPassword: string,
): string {
  if (!currentPassword || !newPassword || !confirmPassword) {
    return "Please complete all password fields.";
  }

  if (newPassword !== confirmPassword) {
    return "New passwords do not match.";
  }

  return "";
}

function extractPasswordError(result: unknown): string {
  if (typeof result !== "object" || result === null) {
    return "Unable to change your password.";
  }

  if (!("errors" in result) || !Array.isArray(result.errors)) {
    return "Unable to change your password.";
  }

  const messages = result.errors
    .filter(
      (item): item is { message: string } =>
        typeof item === "object" &&
        item !== null &&
        "message" in item &&
        typeof item.message === "string",
    )
    .map((item) => item.message);

  return messages.join(" ") || "Unable to change your password.";
}

async function submitPasswordChange(
  currentPassword: string,
  newPassword: string,
  csrfToken: string,
): Promise<void> {
  const response = await fetch("/_allauth/browser/v1/account/password/change", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });

  if (response.ok) return;

  if (response.status === 401 || response.status === 403) {
    throw new Error(
      "Your session may have expired or the security check failed. Please sign in again.",
    );
  }

  if (response.status === 404 || response.status === 405) {
    throw new Error(
      "Password changes are not available through this endpoint.",
    );
  }

  const result: unknown = await response.json().catch(() => null);

  throw new Error(extractPasswordError(result));
}

function SidebarButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={`w-full rounded-full px-5 py-4 text-left text-base font-bold tracking-wide transition lg:text-center ${
        active
          ? "bg-indigo-600 text-white shadow-lg shadow-indigo-950/40"
          : "bg-surface-hover text-subtle hover:bg-surface"
      }`}
    >
      {label}
    </button>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-wrap items-start gap-3 border-b border-border pb-5">
      <span className="min-w-36 font-bold text-foreground">{label}</span>

      <span className="break-words text-subtle">{value}</span>
    </div>
  );
}

function AvatarPreview({
  avatar,
  displayName,
}: {
  avatar: string;
  displayName: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-5">
      <span className="font-bold">AVATAR:</span>

      {avatar ? (
        <Image
          src={avatar}
          alt={`${displayName}'s avatar`}
          width={80}
          height={80}
          unoptimized
          className="h-20 w-20 rounded-full border-2 border-indigo-400 object-cover"
        />
      ) : (
        <div className="flex h-20 w-20 items-center justify-center rounded-full border-2 border-indigo-400 bg-surface-hover">
          <UserRound className="h-9 w-9 text-subtle" />
        </div>
      )}

      <Link
        href="/profile/edit"
        className="inline-flex items-center gap-2 rounded-xl border border-indigo-500 px-4 py-2 text-sm font-semibold text-link transition hover:bg-indigo-500/20"
      >
        <Camera className="h-4 w-4" />
        Change Avatar
      </Link>
    </div>
  );
}

function AccountDetails({
  profile,
  userAvatar,
  emails,
  emailLoading,
  emailError,
}: {
  profile: UserProfile;
  userAvatar: string;
  emails: EmailAddress[];
  emailLoading: boolean;
  emailError: string;
}) {
  const displayName = profile.display_name || "QuestLog Player";

  const primaryEmail = emails.find((email) => email.primary) || emails[0];

  return (
    <section className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-3xl font-black tracking-wide sm:text-4xl">
          PERSONAL DETAILS
        </h2>

        <Link
          href="/profile/edit"
          className="rounded-xl bg-indigo-600 text-white px-5 py-2.5 text-sm font-semibold transition hover:bg-indigo-500"
        >
          Edit Profile
        </Link>
      </div>

      <div className="rounded-2xl border border-border bg-surface p-6 sm:p-8">
        <div className="space-y-6 text-lg">
          <DetailRow label="DISPLAY NAME:" value={displayName} />

          <DetailRow
            label="BGG USERNAME:"
            value={profile.bgg_username || "Not connected"}
          />

          <DetailRow label="PROFILE PRIVACY:" value={profile.privacy_level} />

          <DetailRow label="BIO:" value={profile.bio || "No bio added"} />

          <div className="border-b border-border pb-5">
            <div className="flex flex-wrap items-center gap-3">
              <span className="min-w-36 font-bold">EMAIL:</span>

              <div>
                {emailLoading ? (
                  <span className="text-muted">Loading email...</span>
                ) : primaryEmail ? (
                  <div className="space-y-1">
                    <p className="break-all text-subtle">
                      {primaryEmail.email}
                    </p>

                    <p
                      className={`text-sm ${
                        primaryEmail.verified
                          ? "text-emerald-400 [html[data-theme=light]_&]:text-emerald-700"
                          : "text-amber-400 [html[data-theme=light]_&]:text-amber-700"
                      }`}
                    >
                      {primaryEmail.verified ? "Verified" : "Not verified"}
                    </p>
                  </div>
                ) : (
                  <span className="text-sm text-muted">
                    {emailError || "No email available"}
                  </span>
                )}
              </div>
            </div>
          </div>

          <AvatarPreview avatar={userAvatar} displayName={displayName} />
        </div>
      </div>
    </section>
  );
}

function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPasswords, setShowPasswords] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleChangePassword(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (saving) return;

    setMessage("");
    setError("");

    const validationError = validatePasswordChange(
      currentPassword,
      newPassword,
      confirmPassword,
    );

    if (validationError) {
      setError(validationError);
      return;
    }

    const csrfToken = getCsrfToken();

    if (!csrfToken) {
      setError(
        "Missing security token. Please refresh the page and try again.",
      );
      return;
    }

    setSaving(true);

    try {
      await submitPasswordChange(currentPassword, newPassword, csrfToken);

      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage("Your password has been changed successfully.");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to change your password.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <div className="mb-5 flex items-center gap-3">
        <LockKeyhole className="h-7 w-7 text-link" />

        <h3 className="text-xl font-bold">Change Password</h3>
      </div>

      <p className="mb-6 text-sm text-muted">
        Update the password used to sign in to QuestLog.
      </p>

      <form
        onSubmit={(event) => void handleChangePassword(event)}
        className="max-w-lg space-y-5"
      >
        {[
          {
            label: "Current Password",
            value: currentPassword,
            onChange: setCurrentPassword,
            autocomplete: "current-password",
          },
          {
            label: "New Password",
            value: newPassword,
            onChange: setNewPassword,
            autocomplete: "new-password",
          },
          {
            label: "Confirm New Password",
            value: confirmPassword,
            onChange: setConfirmPassword,
            autocomplete: "new-password",
          },
        ].map((field) => (
          <div key={field.label}>
            <label className="mb-2 block text-sm font-semibold">
              {field.label}
            </label>

            <input
              type={showPasswords ? "text" : "password"}
              value={field.value}
              onChange={(event) => field.onChange(event.target.value)}
              autoComplete={field.autocomplete}
              required
              className="w-full rounded-xl border border-border bg-input px-4 py-3 text-foreground outline-none transition focus:border-indigo-500"
            />
          </div>
        ))}

        <button
          type="button"
          onClick={() => setShowPasswords((value) => !value)}
          className="inline-flex items-center gap-2 text-sm text-link hover:text-link"
        >
          {showPasswords ? (
            <EyeOff className="h-4 w-4" />
          ) : (
            <Eye className="h-4 w-4" />
          )}

          {showPasswords ? "Hide passwords" : "Show passwords"}
        </button>

        <div>
          <button
            type="submit"
            disabled={saving}
            className="rounded-xl bg-indigo-600 text-white px-6 py-3 font-semibold transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {saving ? "Updating..." : "Update Password"}
          </button>
        </div>

        {error && (
          <p
            role="alert"
            className="text-sm text-red-400 [html[data-theme=light]_&]:text-red-700"
          >
            {error}
          </p>
        )}

        {message && (
          <p
            role="status"
            className="text-sm text-emerald-400 [html[data-theme=light]_&]:text-emerald-700"
          >
            {message}
          </p>
        )}
      </form>
    </div>
  );
}

type AuthenticatorRecord = {
  type?: string;
  total_code_count?: number;
  unused_code_count?: number;
  unused_codes?: string[];
};
type MFAAction = "disable" | "view" | "regenerate";
const MFA_BASE = "/_allauth/browser/v1/account/authenticators";

async function mfaRequest(
  path: string,
  method = "GET",
  body?: object,
): Promise<Response> {
  const csrfToken = getCsrfToken();
  if (method !== "GET" && !csrfToken) {
    throw new Error("Missing security token. Refresh the page and try again.");
  }
  return fetch(path, {
    method,
    credentials: "include",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(method !== "GET" ? { "X-CSRFToken": csrfToken } : {}),
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
}

async function mfaError(response: Response, fallback: string): Promise<Error> {
  const payload: unknown = await response.json().catch(() => null);
  if (response.status === 401 || response.status === 403) {
    const data = payload as {
      data?: { flows?: Array<{ id?: string }> };
      meta?: { is_authenticated?: boolean };
    } | null;
    if (data?.data?.flows?.some((flow) => flow.id === "reauthenticate")) {
      return new Error(
        "Password confirmation expired. Please confirm your password and try again.",
      );
    }
    return new Error(
      "Your session expired or another security check is required. Please sign in again if this continues.",
    );
  }
  const errors = (payload as { errors?: Array<{ message?: string }> } | null)
    ?.errors;
  return new Error(
    errors
      ?.map((item) => item.message)
      .filter(Boolean)
      .join(" ") || fallback,
  );
}

async function fetchMFAStatus(
  signal?: AbortSignal,
): Promise<AuthenticatorRecord[]> {
  const response = await fetch(MFA_BASE, {
    credentials: "include",
    cache: "no-store",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok)
    throw await mfaError(response, "Unable to check your MFA status.");
  const payload: unknown = await response.json();
  if (
    !payload ||
    typeof payload !== "object" ||
    !("data" in payload) ||
    !Array.isArray(payload.data)
  ) {
    throw new Error("Unexpected MFA status response from the server.");
  }
  const items = payload.data as AuthenticatorRecord[];
  return items;
}

async function performMFAAction(
  selected: MFAAction,
): Promise<{ codes: string[]; message: string }> {
  const requests = {
    disable: { path: `${MFA_BASE}/totp`, method: "DELETE" },
    regenerate: { path: `${MFA_BASE}/recovery-codes`, method: "POST" },
    view: { path: `${MFA_BASE}/recovery-codes`, method: "GET" },
  };
  const { path, method } = requests[selected];
  const response = await mfaRequest(path, method);
  if (!response.ok)
    throw await mfaError(response, "Unable to complete the MFA action.");
  if (selected === "disable") {
    return { codes: [], message: "Authenticator-app MFA has been disabled." };
  }
  const payload: unknown = await response.json();
  const data = (payload as { data?: AuthenticatorRecord } | null)?.data;
  if (!Array.isArray(data?.unused_codes)) {
    return {
      codes: [],
      message:
        "Recovery-code information loaded, but the codes are not available to display. They may have been shown previously.",
    };
  }
  return {
    codes: data.unused_codes,
    message:
      selected === "regenerate"
        ? "New recovery codes generated. Previous codes are no longer valid. Save these now."
        : "Save these recovery codes in a secure location. They may only be shown once.",
  };
}

function MFAEnabledControls({
  recovery,
  busy,
  onSelect,
}: {
  recovery: AuthenticatorRecord | null;
  busy: boolean;
  onSelect: (action: MFAAction) => void;
}) {
  return (
    <>
      <p
        role="status"
        className="font-semibold text-emerald-400 [html[data-theme=light]_&]:text-emerald-700"
      >
        Authenticator app enabled
      </p>
      <button
        type="button"
        disabled={busy}
        onClick={() => onSelect("disable")}
        className="rounded-xl border border-red-500 px-4 py-2 text-sm font-semibold text-red-400 hover:bg-red-500/10 disabled:opacity-50"
      >
        Disable MFA
      </button>
      <div className="border-t border-border pt-5 space-y-3">
        <h4 className="font-bold">Recovery Codes</h4>
        <p className="text-sm text-muted">
          {recovery
            ? `${recovery.unused_code_count ?? "?"} of ${recovery.total_code_count ?? "?"} recovery codes remaining.`
            : "No recovery codes found."}
        </p>
        <p className="text-sm text-muted">
          Recovery codes may only be shown once. Generating a new set
          invalidates all previous codes.
        </p>
        <div className="flex flex-wrap gap-3">
          {recovery && (
            <button
              type="button"
              disabled={busy}
              onClick={() => onSelect("view")}
              className="rounded-xl border border-border px-4 py-2 text-sm font-semibold hover:bg-surface-hover disabled:opacity-50"
            >
              View available codes
            </button>
          )}
          <button
            type="button"
            disabled={busy}
            onClick={() => onSelect("regenerate")}
            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {recovery ? "Regenerate codes" : "Generate recovery codes"}
          </button>
        </div>
      </div>
    </>
  );
}

function MFAActionForm({
  action,
  password,
  busy,
  onSubmit,
  onPasswordChange,
  onCancel,
}: {
  action: MFAAction;
  password: string;
  busy: boolean;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => Promise<void>;
  onPasswordChange: (value: string) => void;
  onCancel: () => void;
}) {
  return (
    <form
      onSubmit={(event) => void onSubmit(event)}
      className="space-y-3 rounded-xl border border-border bg-background p-4"
    >
      <h4 className="font-semibold">
        {action === "disable"
          ? "Confirm disabling MFA"
          : action === "regenerate"
            ? "Confirm recovery-code generation"
            : "View recovery codes"}
      </h4>
      <p className="text-sm text-muted">
        {action === "disable"
          ? "This removes authenticator-app protection from your account."
          : action === "regenerate"
            ? "All previously generated recovery codes will immediately stop working."
            : "For your security, confirm your password to view codes if they have not already been shown."}
      </p>
      <label htmlFor="mfa-password" className="block text-sm font-semibold">
        Current password
      </label>
      <input
        id="mfa-password"
        type="password"
        autoComplete="current-password"
        required
        value={password}
        disabled={busy}
        onChange={(event) => onPasswordChange(event.target.value)}
        className="w-full max-w-md rounded-xl border border-border bg-input px-4 py-3 text-foreground"
      />
      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={busy || !password}
          className="rounded-xl bg-indigo-600 px-4 py-2 font-semibold text-white disabled:opacity-50"
        >
          {busy ? "Processing..." : "Confirm"}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onCancel}
          className="rounded-xl border border-border px-4 py-2 font-semibold disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

function MFASettingsCard() {
  function startAction(selected: MFAAction) {
    setCodes([]);
    setMessage("");
    setError("");
    setAction(selected);
  }

  const [status, setStatus] = useState<
    "loading" | "enabled" | "disabled" | "error"
  >("loading");
  const [recovery, setRecovery] = useState<AuthenticatorRecord | null>(null);
  const [action, setAction] = useState<MFAAction | null>(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [codes, setCodes] = useState<string[]>([]);

  function applyStatus(items: AuthenticatorRecord[]) {
    setStatus(
      items.some((item) => item.type?.toLowerCase() === "totp")
        ? "enabled"
        : "disabled",
    );
    setRecovery(
      items.find((item) => item.type?.toLowerCase() === "recovery_codes") ??
        null,
    );
  }

  async function refreshStatus() {
    applyStatus(await fetchMFAStatus());
  }

  useEffect(() => {
    const controller = new AbortController();
    void fetchMFAStatus(controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return;
        setStatus(
          items.some((item) => item.type?.toLowerCase() === "totp")
            ? "enabled"
            : "disabled",
        );
        setRecovery(
          items.find((item) => item.type?.toLowerCase() === "recovery_codes") ??
            null,
        );
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error ? err.message : "Unable to check MFA status.",
          );
          setStatus("error");
        }
      });
    return () => controller.abort();
  }, []);

  function cancelAction() {
    setAction(null);
    setPassword("");
    setError("");
  }

  async function handleAction(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!action || busy || !password) return;
    setBusy(true);
    setError("");
    setMessage("");
    setCodes([]);
    const selected = action;
    try {
      const reauth = await mfaRequest(
        "/_allauth/browser/v1/auth/reauthenticate",
        "POST",
        { password },
      );
      if (!reauth.ok)
        throw await mfaError(reauth, "Unable to confirm your password.");
      setPassword("");
      const result = await performMFAAction(selected);
      setCodes(result.codes);
      setMessage(result.message);
      setAction(null);
      await refreshStatus();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to complete the MFA action.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <div className="flex items-start gap-4">
        <Shield className="mt-1 h-7 w-7 shrink-0 text-emerald-400 [html[data-theme=light]_&]:text-emerald-700" />
        <div className="min-w-0 flex-1 space-y-4">
          <h3 className="text-xl font-bold">Multifactor Authentication</h3>
          <p className="text-subtle">
            Protect your account with an authenticator app.
          </p>
          {status === "loading" && (
            <p role="status" className="text-sm text-muted">
              Checking MFA status...
            </p>
          )}
          {status === "error" && (
            <button
              type="button"
              className="text-link underline"
              onClick={() => {
                setStatus("loading");
                setError("");
                void refreshStatus().catch((err: unknown) => {
                  setError(
                    err instanceof Error
                      ? err.message
                      : "Unable to check MFA status.",
                  );
                  setStatus("error");
                });
              }}
            >
              Retry status check
            </button>
          )}
          {status === "disabled" && (
            <>
              <p className="text-sm text-muted">
                Authenticator app not enabled
              </p>
              <Link
                href="/mfa-setup?from=settings"
                className="inline-flex rounded-xl bg-indigo-600 px-5 py-2.5 font-semibold text-white hover:bg-indigo-500"
              >
                Enable MFA
              </Link>
            </>
          )}
          {status === "enabled" && (
            <MFAEnabledControls
              recovery={recovery}
              busy={busy}
              onSelect={startAction}
            />
          )}
          {action && (
            <MFAActionForm
              action={action}
              password={password}
              busy={busy}
              onSubmit={handleAction}
              onPasswordChange={setPassword}
              onCancel={cancelAction}
            />
          )}
          {error && (
            <p
              role="alert"
              className="text-sm text-red-400 [html[data-theme=light]_&]:text-red-700"
            >
              {error}
            </p>
          )}
          {message && (
            <p
              role="status"
              className="text-sm text-emerald-400 [html[data-theme=light]_&]:text-emerald-700"
            >
              {message}
            </p>
          )}
          {codes.length > 0 && (
            <div className="space-y-3 rounded-xl border border-border bg-background p-4">
              <h4 className="font-bold">Your recovery codes</h4>
              <p className="text-sm text-muted">
                Store these somewhere safe. Do not share them or take
                screenshots.
              </p>
              <ul className="grid gap-2 sm:grid-cols-2">
                {codes.map((code, index) => (
                  <li
                    key={index}
                    className="rounded-lg border border-border bg-input p-2 font-mono text-sm select-all"
                  >
                    {code}
                  </li>
                ))}
              </ul>
              <button
                type="button"
                onClick={() => {
                  setCodes([]);
                  setMessage("Recovery codes hidden.");
                }}
                className="rounded-xl border border-border px-4 py-2 text-sm font-semibold"
              >
                I&apos;ve saved my codes — hide them
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SecuritySettings({
  emails,
  emailLoading,
  emailError,
}: {
  emails: EmailAddress[];
  emailLoading: boolean;
  emailError: string;
}) {
  return (
    <section className="space-y-8">
      <h2 className="text-3xl font-black tracking-wide sm:text-4xl">
        DATA AND SECURITY
      </h2>

      <div className="space-y-6">
        <div className="rounded-2xl border border-border bg-surface p-6">
          <div className="flex items-start gap-4">
            <Mail className="mt-1 h-7 w-7 shrink-0 text-link" />

            <div className="min-w-0">
              <h3 className="text-xl font-bold">Email Addresses</h3>

              {emailLoading ? (
                <p className="mt-3 text-muted">Loading email information...</p>
              ) : emails.length > 0 ? (
                <div className="mt-4 space-y-3">
                  {emails.map((email) => (
                    <div
                      key={email.email}
                      className="flex flex-wrap items-center gap-3"
                    >
                      <span className="break-all text-subtle">
                        {email.email}
                      </span>

                      {email.primary && (
                        <span className="rounded-full bg-indigo-500/20 px-3 py-1 text-xs text-link">
                          Primary
                        </span>
                      )}

                      <span
                        className={`text-xs ${
                          email.verified
                            ? "text-emerald-400 [html[data-theme=light]_&]:text-emerald-700"
                            : "text-amber-400 [html[data-theme=light]_&]:text-amber-700"
                        }`}
                      >
                        {email.verified ? "Verified" : "Unverified"}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-sm text-muted">
                  {emailError || "No email information available."}
                </p>
              )}

              <p className="mt-4 text-sm text-muted">
                Email addresses are read from your authentication account.
                Changing or removing an email address is not yet connected to
                this Settings page.
              </p>
            </div>
          </div>
        </div>

        <ChangePasswordForm />

        <MFASettingsCard />

        <div className="rounded-2xl border border-border bg-surface p-6">
          <h3 className="text-xl font-bold">Account and Game Data</h3>

          <p className="mt-3 text-subtle">
            Game-data clearing and account deletion are not yet available from
            this page.
          </p>

          <div className="mt-6 flex flex-wrap gap-4">
            <button
              type="button"
              disabled
              className="cursor-not-allowed rounded-full bg-red-900/50 [html[data-theme=light]_&]:bg-red-100 px-6 py-3 font-semibold text-muted"
            >
              Clear Game Data
            </button>

            <button
              type="button"
              disabled
              className="cursor-not-allowed rounded-full bg-red-900/50 [html[data-theme=light]_&]:bg-red-100 px-6 py-3 font-semibold text-muted"
            >
              Delete Account
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

function PrivacySettings({
  privacyLevel,
  savedPrivacyLevel,
  saving,
  onChange,
  onSave,
}: {
  privacyLevel: PrivacyLevel;
  savedPrivacyLevel: PrivacyLevel;
  saving: boolean;
  onChange: (value: PrivacyLevel) => void;
  onSave: () => void;
}) {
  return (
    <section className="space-y-8">
      <div>
        <h2 className="text-3xl font-black tracking-wide sm:text-4xl">
          PRIVACY SETTINGS
        </h2>

        <p className="mt-3 text-subtle">
          Choose your profile visibility preference.
        </p>
      </div>

      <div className="rounded-2xl border border-border bg-surface p-6 sm:p-8">
        <h3 className="mb-5 text-xl font-bold">Profile Visibility</h3>

        <fieldset className="space-y-4">
          <legend className="sr-only">Select profile visibility</legend>

          {privacyOptions.map((option) => (
            <label
              key={option.value}
              className={`flex cursor-pointer items-start gap-4 rounded-xl border p-4 transition ${
                privacyLevel === option.value
                  ? "border-indigo-500 bg-indigo-500/10"
                  : "border-border hover:border-link"
              }`}
            >
              <input
                type="radio"
                name="privacy-level"
                value={option.value}
                checked={privacyLevel === option.value}
                onChange={() => onChange(option.value)}
                className="mt-1 h-5 w-5 accent-indigo-500"
              />

              <span>
                <span className="block font-bold">{option.label}</span>

                <span className="mt-1 block text-sm text-muted">
                  {option.description}
                </span>
              </span>
            </label>
          ))}
        </fieldset>

        <button
          type="button"
          onClick={onSave}
          disabled={saving || privacyLevel === savedPrivacyLevel}
          className="mt-7 rounded-xl bg-indigo-600 text-white px-6 py-3 font-semibold transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Privacy Settings"}
        </button>
      </div>

      <div className="rounded-2xl border border-border bg-surface p-6">
        <h3 className="text-xl font-bold">Community Privacy</h3>

        <p className="mt-3 text-subtle">
          Chat permissions, friend-request controls, mature-language filtering,
          and blocked accounts are not yet connected to the backend.
        </p>
      </div>
    </section>
  );
}

function AppearanceSettings() {
  const { theme, setTheme } = useTheme();

  return (
    <section className="space-y-8">
      <h2 className="text-3xl font-black tracking-wide sm:text-4xl">
        APPEARANCE
      </h2>
      <div className="rounded-2xl border border-border bg-surface p-6 sm:p-8">
        <h3 className="text-xl font-bold">Display Theme</h3>
        <p className="mt-2 text-muted">
          Choose how QuestLog looks on this browser.
        </p>
        <fieldset className="mt-6 grid gap-4 sm:grid-cols-2">
          <legend className="sr-only">Display theme</legend>
          {(["light", "dark"] as const).map((mode) => (
            <label
              key={mode}
              className={`cursor-pointer rounded-xl border-2 p-4 transition ${
                theme === mode ? "border-indigo-500" : "border-border"
              }`}
            >
              <div
                aria-hidden="true"
                className={`mb-4 space-y-3 rounded-lg p-3 ${mode === "light" ? "bg-[#F1F5F9]" : "bg-[#0F172A]"}`}
              >
                <div
                  className={`h-3 rounded ${mode === "light" ? "bg-slate-300" : "bg-slate-600"}`}
                />
                <div className="grid grid-cols-3 gap-2">
                  <div
                    className={`h-16 rounded ${mode === "light" ? "bg-white" : "bg-[#1E293B]"}`}
                  />
                  <div
                    className={`col-span-2 h-16 rounded p-2 ${mode === "light" ? "bg-white" : "bg-[#1E293B]"}`}
                  >
                    <div className="h-2 w-3/4 rounded bg-indigo-500" />
                  </div>
                </div>
              </div>
              <span className="flex items-center gap-3 font-semibold">
                <input
                  type="radio"
                  name="display-theme"
                  value={mode}
                  checked={theme === mode}
                  onChange={() => setTheme(mode)}
                  className="h-5 w-5 accent-indigo-500"
                />
                {mode === "light" ? "Light" : "Dark"}
              </span>
            </label>
          ))}
        </fieldset>
        <p role="status" className="mt-5 text-sm text-muted">
          {theme === "light" ? "Light" : "Dark"} mode is active. Your preference
          is saved on this browser when storage is available.
        </p>
      </div>
    </section>
  );
}

function SettingsFeedback({
  error,
  success,
}: {
  error: string;
  success: string;
}) {
  return (
    <>
      {error && (
        <p
          role="alert"
          className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-300 [html[data-theme=light]_&]:text-red-700"
        >
          {error}
        </p>
      )}

      {success && (
        <p
          role="status"
          className="mt-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-emerald-300 [html[data-theme=light]_&]:text-emerald-700"
        >
          {success}
        </p>
      )}
    </>
  );
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("account");

  const [profile, setProfile] = useState<UserProfile | null>(null);

  const [emails, setEmails] = useState<EmailAddress[]>([]);
  const [emailLoading, setEmailLoading] = useState(true);
  const [emailError, setEmailError] = useState("");

  const [privacyLevel, setPrivacyLevel] = useState<PrivacyLevel>("PUBLIC");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadSettings() {
      try {
        const data = await fetchProfile(controller.signal);

        if (controller.signal.aborted) return;

        setProfile(data);
        setPrivacyLevel(data.privacy_level);
      } catch (err) {
        if (controller.signal.aborted) return;

        setError(
          err instanceof Error ? err.message : "Unable to load settings.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    async function loadEmails() {
      try {
        const data = await fetchEmails(controller.signal);

        if (!controller.signal.aborted) {
          setEmails(data);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setEmailError(
            err instanceof Error
              ? err.message
              : "Unable to load email information.",
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setEmailLoading(false);
        }
      }
    }

    void loadSettings();
    void loadEmails();

    return () => controller.abort();
  }, []);

  async function handleSavePrivacy() {
    if (!profile || saving) return;

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const updated = await savePrivacyLevel(privacyLevel);

      setProfile(updated);
      setPrivacyLevel(updated.privacy_level);
      setSuccess("Your privacy settings have been saved.");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save privacy settings.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-background px-5 py-8 text-foreground sm:px-10">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex items-center gap-3 border-b border-border pb-5">
          <Settings className="h-8 w-8 text-link" />

          <h1 className="text-3xl font-black tracking-wide sm:text-4xl">
            USER SETTINGS
          </h1>
        </div>

        <div className="grid gap-10 lg:grid-cols-[280px_minmax(0,1fr)] lg:gap-12">
          <nav aria-label="Settings sections" className="flex flex-col gap-4">
            <SidebarButton
              active={activeTab === "account"}
              label="ACCOUNT DETAILS"
              onClick={() => {
                setActiveTab("account");
                setError("");
                setSuccess("");
              }}
            />

            <SidebarButton
              active={activeTab === "appearance"}
              label="APPEARANCE"
              onClick={() => {
                setActiveTab("appearance");
                setError("");
                setSuccess("");
              }}
            />

            <SidebarButton
              active={activeTab === "security"}
              label="DATA AND SECURITY"
              onClick={() => {
                setActiveTab("security");
                setError("");
                setSuccess("");
              }}
            />

            <SidebarButton
              active={activeTab === "privacy"}
              label="PRIVACY SETTINGS"
              onClick={() => {
                setActiveTab("privacy");
                setError("");
                setSuccess("");
              }}
            />
          </nav>

          <div className="min-w-0">
            {loading ? (
              <p className="text-subtle">Loading your settings...</p>
            ) : !profile ? (
              <div className="rounded-2xl border border-red-500/30 bg-surface p-6">
                <h2 className="mb-3 text-2xl font-bold">
                  Settings Unavailable
                </h2>

                <p
                  role="alert"
                  className="mb-5 text-red-400 [html[data-theme=light]_&]:text-red-700"
                >
                  {error || "Unable to load your account."}
                </p>

                <Link
                  href="/login"
                  className="inline-block rounded-lg bg-indigo-600 text-white px-5 py-2 font-semibold hover:bg-indigo-500"
                >
                  Go to Login
                </Link>
              </div>
            ) : (
              <>
                {activeTab === "account" && (
                  <AccountDetails
                    profile={profile}
                    userAvatar={profile.avatar || ""}
                    emails={emails}
                    emailLoading={emailLoading}
                    emailError={emailError}
                  />
                )}

                {activeTab === "appearance" && <AppearanceSettings />}

                {activeTab === "security" && (
                  <SecuritySettings
                    emails={emails}
                    emailLoading={emailLoading}
                    emailError={emailError}
                  />
                )}

                {activeTab === "privacy" && (
                  <PrivacySettings
                    privacyLevel={privacyLevel}
                    savedPrivacyLevel={profile.privacy_level}
                    saving={saving}
                    onChange={(value) => {
                      setPrivacyLevel(value);
                      setSuccess("");
                    }}
                    onSave={() => void handleSavePrivacy()}
                  />
                )}

                <SettingsFeedback error={error} success={success} />
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
