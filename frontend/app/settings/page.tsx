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

type SettingsTab = "account" | "security" | "privacy";
type PrivacyLevel = "PUBLIC" | "FRIENDS" | "PRIVATE";

type UserProfile = {
  user_id: string;
  display_name: string;
  bio: string;
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

function getSavedAvatar(): string {
  try {
    const avatar = localStorage.getItem("userAvatar");
    if (avatar) return avatar;

    const saved = localStorage.getItem("userProfile");
    if (!saved) return "";

    const parsed = JSON.parse(saved) as { avatar?: string };
    return parsed.avatar || "";
  } catch {
    return "";
  }
}

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
          : "bg-gray-700 text-gray-200 hover:bg-gray-600"
      }`}
    >
      {label}
    </button>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-wrap items-start gap-3 border-b border-gray-700 pb-5">
      <span className="min-w-36 font-bold text-white">{label}</span>

      <span className="break-words text-gray-300">{value}</span>
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
        <div className="flex h-20 w-20 items-center justify-center rounded-full border-2 border-indigo-400 bg-gray-700">
          <UserRound className="h-9 w-9 text-gray-300" />
        </div>
      )}

      <Link
        href="/avatar-selection"
        className="inline-flex items-center gap-2 rounded-xl border border-indigo-500 px-4 py-2 text-sm font-semibold text-indigo-200 transition hover:bg-indigo-500/20"
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
          className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold transition hover:bg-indigo-500"
        >
          Edit Profile
        </Link>
      </div>

      <div className="rounded-2xl border border-gray-700 bg-[#1E293B] p-6 sm:p-8">
        <div className="space-y-6 text-lg">
          <DetailRow label="DISPLAY NAME:" value={displayName} />

          <DetailRow
            label="BGG USERNAME:"
            value={profile.bgg_username || "Not connected"}
          />

          <DetailRow label="PROFILE PRIVACY:" value={profile.privacy_level} />

          <DetailRow label="BIO:" value={profile.bio || "No bio added"} />

          <div className="border-b border-gray-700 pb-5">
            <div className="flex flex-wrap items-center gap-3">
              <span className="min-w-36 font-bold">EMAIL:</span>

              <div>
                {emailLoading ? (
                  <span className="text-gray-400">Loading email...</span>
                ) : primaryEmail ? (
                  <div className="space-y-1">
                    <p className="break-all text-gray-300">
                      {primaryEmail.email}
                    </p>

                    <p
                      className={`text-sm ${
                        primaryEmail.verified
                          ? "text-emerald-400"
                          : "text-amber-400"
                      }`}
                    >
                      {primaryEmail.verified ? "Verified" : "Not verified"}
                    </p>
                  </div>
                ) : (
                  <span className="text-sm text-gray-400">
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
    <div className="rounded-2xl border border-gray-700 bg-[#1E293B] p-6">
      <div className="mb-5 flex items-center gap-3">
        <LockKeyhole className="h-7 w-7 text-indigo-400" />

        <h3 className="text-xl font-bold">Change Password</h3>
      </div>

      <p className="mb-6 text-sm text-gray-400">
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
              className="w-full rounded-xl border border-gray-600 bg-[#0F172A] px-4 py-3 text-white outline-none transition focus:border-indigo-500"
            />
          </div>
        ))}

        <button
          type="button"
          onClick={() => setShowPasswords((value) => !value)}
          className="inline-flex items-center gap-2 text-sm text-indigo-300 hover:text-indigo-200"
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
            className="rounded-xl bg-indigo-600 px-6 py-3 font-semibold transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {saving ? "Updating..." : "Update Password"}
          </button>
        </div>

        {error && (
          <p role="alert" className="text-sm text-red-400">
            {error}
          </p>
        )}

        {message && (
          <p role="status" className="text-sm text-emerald-400">
            {message}
          </p>
        )}
      </form>
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
        <div className="rounded-2xl border border-gray-700 bg-[#1E293B] p-6">
          <div className="flex items-start gap-4">
            <Mail className="mt-1 h-7 w-7 shrink-0 text-indigo-400" />

            <div className="min-w-0">
              <h3 className="text-xl font-bold">Email Addresses</h3>

              {emailLoading ? (
                <p className="mt-3 text-gray-400">
                  Loading email information...
                </p>
              ) : emails.length > 0 ? (
                <div className="mt-4 space-y-3">
                  {emails.map((email) => (
                    <div
                      key={email.email}
                      className="flex flex-wrap items-center gap-3"
                    >
                      <span className="break-all text-gray-200">
                        {email.email}
                      </span>

                      {email.primary && (
                        <span className="rounded-full bg-indigo-500/20 px-3 py-1 text-xs text-indigo-200">
                          Primary
                        </span>
                      )}

                      <span
                        className={`text-xs ${
                          email.verified ? "text-emerald-400" : "text-amber-400"
                        }`}
                      >
                        {email.verified ? "Verified" : "Unverified"}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-sm text-gray-400">
                  {emailError || "No email information available."}
                </p>
              )}

              <p className="mt-4 text-sm text-gray-400">
                Email addresses are read from your authentication account.
                Changing or removing an email address is not yet connected to
                this Settings page.
              </p>
            </div>
          </div>
        </div>

        <ChangePasswordForm />

        <div className="rounded-2xl border border-gray-700 bg-[#1E293B] p-6">
          <div className="flex items-start gap-4">
            <Shield className="mt-1 h-7 w-7 shrink-0 text-emerald-400" />

            <div>
              <h3 className="text-xl font-bold">Multifactor Authentication</h3>

              <p className="mt-2 text-gray-300">
                QuestLog supports MFA during account setup.
              </p>

              <p className="mt-3 text-sm text-gray-400">
                Your current MFA status and management options are not yet
                connected to this page.
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-gray-700 bg-[#1E293B] p-6">
          <h3 className="text-xl font-bold">Account and Game Data</h3>

          <p className="mt-3 text-gray-300">
            Game-data clearing and account deletion are not yet available from
            this page.
          </p>

          <div className="mt-6 flex flex-wrap gap-4">
            <button
              type="button"
              disabled
              className="cursor-not-allowed rounded-full bg-red-900/50 px-6 py-3 font-semibold text-gray-400"
            >
              Clear Game Data
            </button>

            <button
              type="button"
              disabled
              className="cursor-not-allowed rounded-full bg-red-900/50 px-6 py-3 font-semibold text-gray-400"
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

        <p className="mt-3 text-gray-300">
          Choose your profile visibility preference.
        </p>
      </div>

      <div className="rounded-2xl border border-gray-700 bg-[#1E293B] p-6 sm:p-8">
        <h3 className="mb-5 text-xl font-bold">Profile Visibility</h3>

        <fieldset className="space-y-4">
          <legend className="sr-only">Select profile visibility</legend>

          {privacyOptions.map((option) => (
            <label
              key={option.value}
              className={`flex cursor-pointer items-start gap-4 rounded-xl border p-4 transition ${
                privacyLevel === option.value
                  ? "border-indigo-500 bg-indigo-500/10"
                  : "border-gray-600 hover:border-gray-500"
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

                <span className="mt-1 block text-sm text-gray-400">
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
          className="mt-7 rounded-xl bg-indigo-600 px-6 py-3 font-semibold transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Privacy Settings"}
        </button>
      </div>

      <div className="rounded-2xl border border-gray-700 bg-[#1E293B] p-6">
        <h3 className="text-xl font-bold">Community Privacy</h3>

        <p className="mt-3 text-gray-300">
          Chat permissions, friend-request controls, mature-language filtering,
          and blocked accounts are not yet connected to the backend.
        </p>
      </div>
    </section>
  );
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("account");

  const [profile, setProfile] = useState<UserProfile | null>(null);

  const [userAvatar, setUserAvatar] = useState("");

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
        const avatar = getSavedAvatar();

        if (controller.signal.aborted) return;

        setProfile(data);
        setPrivacyLevel(data.privacy_level);
        setUserAvatar(avatar);
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
    <main className="min-h-screen bg-[#0F172A] px-5 py-8 text-white sm:px-10">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex items-center gap-3 border-b border-gray-600 pb-5">
          <Settings className="h-8 w-8 text-indigo-400" />

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
              <p className="text-gray-300">Loading your settings...</p>
            ) : !profile ? (
              <div className="rounded-2xl border border-red-500/30 bg-gray-800 p-6">
                <h2 className="mb-3 text-2xl font-bold">
                  Settings Unavailable
                </h2>

                <p role="alert" className="mb-5 text-red-400">
                  {error || "Unable to load your account."}
                </p>

                <Link
                  href="/login"
                  className="inline-block rounded-lg bg-indigo-600 px-5 py-2 font-semibold hover:bg-indigo-500"
                >
                  Go to Login
                </Link>
              </div>
            ) : (
              <>
                {activeTab === "account" && (
                  <AccountDetails
                    profile={profile}
                    userAvatar={userAvatar}
                    emails={emails}
                    emailLoading={emailLoading}
                    emailError={emailError}
                  />
                )}

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

                {error && (
                  <p
                    role="alert"
                    className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-300"
                  >
                    {error}
                  </p>
                )}

                {success && (
                  <p
                    role="status"
                    className="mt-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-emerald-300"
                  >
                    {success}
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
