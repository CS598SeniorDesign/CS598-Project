"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import { Settings, Shield, UserRound, LockKeyhole } from "lucide-react";

type SettingsTab = "account" | "security" | "privacy";
type PrivacyLevel = "PUBLIC" | "FRIENDS" | "PRIVATE";

type UserProfile = {
  user_id: string;
  display_name: string;
  bio: string;
  privacy_level: PrivacyLevel;
  bgg_username: string;
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

async function fetchProfile(signal: AbortSignal): Promise<UserProfile> {
  const response = await fetch("/api/v1/profile/", {
    method: "GET",
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

async function savePrivacyLevel(
  privacyLevel: PrivacyLevel,
): Promise<UserProfile> {
  const response = await fetch("/api/v1/profile/", {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      privacy_level: privacyLevel,
    }),
  });

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error(
        "Unable to save privacy settings. Check your login session and CSRF configuration.",
      );
    }

    throw new Error("Unable to save your privacy settings.");
  }

  return (await response.json()) as UserProfile;
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
      <span className="break-all text-gray-300">{value}</span>
    </div>
  );
}

function AccountDetails({
  profile,
  userAvatar,
}: {
  profile: UserProfile;
  userAvatar: string;
}) {
  const displayName = profile.display_name || "QuestLog Player";

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

          <div className="flex flex-wrap items-center gap-5">
            <span className="font-bold">AVATAR:</span>

            {userAvatar ? (
              <Image
                src={userAvatar}
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
          </div>
        </div>
      </div>

      <p className="text-sm text-gray-400">
        Email and password management are not available through the current
        profile API.
      </p>
    </section>
  );
}

function SecuritySettings() {
  return (
    <section className="space-y-8">
      <h2 className="text-3xl font-black tracking-wide sm:text-4xl">
        DATA AND SECURITY
      </h2>

      <div className="space-y-6">
        <div className="rounded-2xl border border-gray-700 bg-[#1E293B] p-6">
          <div className="flex items-start gap-4">
            <Shield className="mt-1 h-7 w-7 shrink-0 text-emerald-400" />

            <div>
              <h3 className="text-xl font-bold">Multifactor Authentication</h3>

              <p className="mt-2 text-gray-300">
                QuestLog supports MFA during account setup. Managing MFA from
                this Settings page is not yet connected.
              </p>

              <p className="mt-3 text-sm text-gray-400">
                Your current MFA status cannot be determined from the profile
                endpoint.
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-gray-700 bg-[#1E293B] p-6">
          <div className="flex items-start gap-4">
            <LockKeyhole className="mt-1 h-7 w-7 shrink-0 text-indigo-400" />

            <div>
              <h3 className="text-xl font-bold">Account and Game Data</h3>

              <p className="mt-2 text-gray-300">
                Game-data clearing and account deletion are not yet available
                from this page.
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

function SettingsPanel({
  activeTab,
  profile,
  userAvatar,
  privacyLevel,
  saving,
  onPrivacyChange,
  onSavePrivacy,
}: {
  activeTab: SettingsTab;
  profile: UserProfile;
  userAvatar: string;
  privacyLevel: PrivacyLevel;
  saving: boolean;
  onPrivacyChange: (value: PrivacyLevel) => void;
  onSavePrivacy: () => void;
}) {
  switch (activeTab) {
    case "account":
      return <AccountDetails profile={profile} userAvatar={userAvatar} />;

    case "security":
      return <SecuritySettings />;

    case "privacy":
      return (
        <PrivacySettings
          privacyLevel={privacyLevel}
          savedPrivacyLevel={profile.privacy_level}
          saving={saving}
          onChange={onPrivacyChange}
          onSave={onSavePrivacy}
        />
      );
  }
}

function SettingsBody({
  loading,
  profile,
  error,
  children,
}: {
  loading: boolean;
  profile: UserProfile | null;
  error: string;
  children: React.ReactNode;
}) {
  if (loading) {
    return <p className="text-gray-300">Loading your settings...</p>;
  }

  if (!profile) {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-gray-800 p-6">
        <h2 className="mb-3 text-2xl font-bold">Settings Unavailable</h2>

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
    );
  }

  return <>{children}</>;
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("account");

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [userAvatar, setUserAvatar] = useState("");

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

    void loadSettings();

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

  function handlePrivacyChange(value: PrivacyLevel) {
    setPrivacyLevel(value);
    setSuccess("");
  }

  return (
    <main className="min-h-screen bg-[#0F172A] px-5 py-8 text-white sm:px-10">
      <div className="mx-auto max-w-7xl">
        {/* HEADER */}
        <div className="mb-8 flex items-center gap-3 border-b border-gray-600 pb-5">
          <Settings className="h-8 w-8 text-indigo-400" />

          <h1 className="text-3xl font-black tracking-wide sm:text-4xl">
            USER SETTINGS
          </h1>
        </div>

        <div className="grid gap-10 lg:grid-cols-[280px_minmax(0,1fr)] lg:gap-12">
          {/* SIDEBAR */}
          <nav aria-label="Settings sections" className="flex flex-col gap-4">
            <SidebarButton
              active={activeTab === "account"}
              label="ACCOUNT DETAILS"
              onClick={() => setActiveTab("account")}
            />

            <SidebarButton
              active={activeTab === "security"}
              label="DATA AND SECURITY"
              onClick={() => setActiveTab("security")}
            />

            <SidebarButton
              active={activeTab === "privacy"}
              label="PRIVACY SETTINGS"
              onClick={() => setActiveTab("privacy")}
            />
          </nav>

          {/* RIGHT CONTENT */}
          <div className="min-w-0">
            <SettingsBody loading={loading} profile={profile} error={error}>
              {profile && (
                <SettingsPanel
                  activeTab={activeTab}
                  profile={profile}
                  userAvatar={userAvatar}
                  privacyLevel={privacyLevel}
                  saving={saving}
                  onPrivacyChange={handlePrivacyChange}
                  onSavePrivacy={() => void handleSavePrivacy()}
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
            </SettingsBody>
          </div>
        </div>
      </div>
    </main>
  );
}
