"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Camera, Save, X } from "lucide-react";
import Image from "next/image";
import { motion } from "framer-motion";

type UserProfile = {
  user_id: string;
  display_name: string;
  bio: string;
  privacy_level: "PUBLIC" | "FRIENDS" | "PRIVATE";
  bgg_username: string;
  avatar: string;
};

const AVATARS = Array.from(
  { length: 12 },
  (_, index) => `/avatars/avatar${index + 1}.webp`,
);

type ProfileAppearance = {
  avatar: string;
  cover: string;
};

function getSavedAppearance(): ProfileAppearance {
  let savedAvatar = "";
  let savedCover = "";

  try {
    const saved = localStorage.getItem("userProfile");

    if (saved) {
      const parsed = JSON.parse(saved) as {
        avatar?: string;
        cover?: string;
      };

      savedAvatar = parsed.avatar || "";
      savedCover = parsed.cover || "";
    }

    return {
      avatar: localStorage.getItem("userAvatar") || savedAvatar,
      cover: localStorage.getItem("userCover") || savedCover,
    };
  } catch {
    return {
      avatar: savedAvatar,
      cover: savedCover,
    };
  }
}

function readImage(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Unable to read the image."));

    reader.readAsDataURL(file);
  });
}

async function fetchOwnProfile(signal: AbortSignal): Promise<UserProfile> {
  const response = await fetch("/api/v1/profile/", {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error(
      response.status === 401 || response.status === 403
        ? "Please log in to edit your profile."
        : "Unable to load your profile.",
    );
  }

  return (await response.json()) as UserProfile;
}

function getCsrfToken(): string {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith("csrf_token="));

  return cookie
    ? decodeURIComponent(cookie.substring("csrf_token=".length))
    : "";
}

function extractSaveError(details: unknown): string {
  if (!details || typeof details !== "object") {
    return "Unable to save your profile.";
  }

  const fields = details as Record<string, unknown>;

  for (const field of [
    "avatar",
    "display_name",
    "bio",
    "bgg_username",
    "detail",
  ]) {
    const message = fields[field];

    if (typeof message === "string") {
      return message;
    }

    if (Array.isArray(message) && typeof message[0] === "string") {
      return message[0];
    }
  }

  return "Unable to save your profile.";
}

async function updateOwnProfile(
  displayName: string,
  bio: string,
  bggUsername: string,
  avatar: string,
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
      display_name: displayName,
      bio,
      bgg_username: bggUsername,
      avatar,
    }),
  });

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error(
        "Your session or security token was rejected. Please refresh and try again.",
      );
    }

    const details: unknown = await response.json().catch(() => null);
    throw new Error(extractSaveError(details));
  }

  return (await response.json()) as UserProfile;
}

function saveAppearance(appearance: ProfileAppearance) {
  localStorage.setItem("userAvatar", appearance.avatar);
  localStorage.setItem("userCover", appearance.cover);

  let previous: Record<string, unknown> = {};

  try {
    const saved = localStorage.getItem("userProfile");

    if (saved) {
      const parsed: unknown = JSON.parse(saved);

      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        previous = parsed as Record<string, unknown>;
      }
    }
  } catch {
    previous = {};
  }

  localStorage.setItem(
    "userProfile",
    JSON.stringify({
      ...previous,
      avatar: appearance.avatar,
      cover: appearance.cover,
    }),
  );
}

function ProfileInput({
  label,
  value,
  onChange,
  placeholder,
  maxLength,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  maxLength?: number;
}) {
  return (
    <label className="block space-y-2">
      <span className="block text-sm font-semibold text-gray-200">{label}</span>

      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        maxLength={maxLength}
        className="w-full rounded-xl border border-gray-600 bg-[#0F172A] px-4 py-3 text-white outline-none transition focus:border-indigo-400"
      />
    </label>
  );
}

function CoverEditor({
  cover,
  onChange,
}: {
  cover: string;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <div className="relative h-52 overflow-hidden bg-gradient-to-r from-indigo-900 via-indigo-700 to-emerald-700 sm:h-64">
      {cover && (
        // Uploaded images are stored as local data URLs.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={cover}
          alt="Profile cover preview"
          className="absolute inset-0 h-full w-full object-cover"
        />
      )}

      <label className="absolute bottom-4 right-4 flex cursor-pointer items-center gap-2 rounded-lg bg-black/70 px-4 py-2 text-sm font-semibold transition hover:bg-black/90">
        <Camera className="h-4 w-4" />
        Change Cover
        <input
          type="file"
          accept="image/*"
          className="sr-only"
          onChange={onChange}
        />
      </label>
    </div>
  );
}

function AvatarEditor({
  avatar,
  displayName,
  onChange,
}: {
  avatar: string;
  displayName: string;
  onChange: (avatar: string) => void;
}) {
  const [pickerOpen, setPickerOpen] = useState(false);

  return (
    <div className="relative -mt-16 flex flex-wrap items-end gap-5">
      <div className="relative flex h-28 w-28 shrink-0 items-center justify-center overflow-hidden rounded-full border-4 border-[#1E293B] bg-indigo-600 text-4xl font-bold shadow-lg sm:h-32 sm:w-32">
        {avatar ? (
          <Image
            src={avatar}
            alt="Profile avatar preview"
            width={128}
            height={128}
            unoptimized
            className="h-full w-full object-cover"
          />
        ) : (
          <span>{displayName.charAt(0).toUpperCase() || "Q"}</span>
        )}
      </div>

      <button
        type="button"
        onClick={() => setPickerOpen(true)}
        className="mb-2 inline-flex items-center gap-2 rounded-lg bg-gray-700 px-4 py-2 text-sm font-semibold transition hover:bg-gray-600"
      >
        <Camera className="h-4 w-4" />
        Change Avatar
      </button>

      {pickerOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setPickerOpen(false);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="avatar-picker-title"
            className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl border border-gray-600 bg-[#1E293B] p-5 shadow-2xl sm:p-7"
          >
            <div className="mb-2 flex items-center justify-between gap-4">
              <h2
                id="avatar-picker-title"
                className="text-xl font-bold text-white"
              >
                Choose Your Avatar
              </h2>
              <button
                type="button"
                onClick={() => setPickerOpen(false)}
                aria-label="Close avatar picker"
                className="rounded-lg p-2 text-gray-300 hover:bg-gray-700 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="mb-5 text-sm text-gray-400">
              Pick one of the 12 QuestLog avatars. Save your profile to keep
              your selection.
            </p>
            <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
              {AVATARS.map((option, index) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => {
                    onChange(option);
                    setPickerOpen(false);
                  }}
                  aria-label={`Choose avatar ${index + 1}`}
                  aria-pressed={avatar === option}
                  className={`rounded-xl border-2 p-2 transition hover:bg-gray-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400 ${avatar === option ? "border-indigo-400 bg-indigo-500/20" : "border-gray-700"}`}
                >
                  <Image
                    src={option}
                    alt={`Avatar ${index + 1}`}
                    width={110}
                    height={110}
                    unoptimized
                    className="aspect-square w-full rounded-full object-cover"
                  />
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setPickerOpen(false)}
              className="mt-5 w-full rounded-lg bg-gray-700 px-4 py-2 font-semibold hover:bg-gray-600"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function EditProfilePage() {
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [bggUsername, setBggUsername] = useState("");

  const [appearance, setAppearance] = useState<ProfileAppearance>({
    avatar: "",
    cover: "",
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    async function loadProfile() {
      try {
        const profile = await fetchOwnProfile(controller.signal);
        const savedAppearance = getSavedAppearance();

        if (controller.signal.aborted) return;

        setDisplayName(profile.display_name || "");
        setBio(profile.bio || "");
        setBggUsername(profile.bgg_username || "");
        setAppearance({
          ...savedAppearance,
          avatar: profile.avatar || savedAppearance.avatar,
        });
      } catch (err) {
        if (controller.signal.aborted) return;

        setLoadFailed(true);
        setError(
          err instanceof Error ? err.message : "Unable to load your profile.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadProfile();

    return () => controller.abort();
  }, []);

  async function handleImageChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Please select a valid image file.");
      return;
    }

    try {
      const image = await readImage(file);

      setAppearance((previous) => ({
        ...previous,
        cover: image,
      }));

      setError("");
    } catch {
      setError("Unable to load the selected image.");
    }
  }

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (saving || loadFailed) return;

    setSaving(true);
    setError("");

    try {
      const updatedProfile = await updateOwnProfile(
        displayName.trim(),
        bio,
        bggUsername.trim(),
        appearance.avatar,
      );

      saveAppearance({ ...appearance, avatar: updatedProfile.avatar });

      window.location.replace("/profile");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save your profile.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-[#0F172A] p-8 text-white">
        <p className="text-gray-300">Loading your profile...</p>
      </main>
    );
  }

  if (loadFailed) {
    return (
      <main className="min-h-screen bg-[#0F172A] p-8 text-white">
        <h1 className="mb-4 text-3xl font-bold">Edit Profile</h1>

        <p role="alert" className="mb-6 text-red-400">
          {error}
        </p>

        <Link
          href="/login"
          className="rounded-xl bg-indigo-600 px-5 py-3 font-semibold hover:bg-indigo-500"
        >
          Go to Login
        </Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0F172A] px-4 py-8 text-[#F8FAFC] sm:px-8">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="mx-auto max-w-4xl"
      >
        <Link
          href="/profile"
          className="mb-7 inline-flex items-center gap-2 text-gray-300 transition hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Profile
        </Link>

        <div className="mb-8">
          <h1 className="text-3xl font-bold">Edit Profile</h1>

          <p className="mt-2 text-sm text-gray-400">
            Customize your QuestLog identity and appearance.
          </p>
        </div>

        <form
          onSubmit={(event) => void handleSave(event)}
          className="overflow-hidden rounded-2xl border border-gray-700 bg-[#1E293B] shadow-xl"
        >
          <CoverEditor
            cover={appearance.cover}
            onChange={(event) => void handleImageChange(event)}
          />

          <div className="space-y-8 px-6 pb-8 sm:px-10">
            <AvatarEditor
              avatar={appearance.avatar}
              displayName={displayName}
              onChange={(avatar) =>
                setAppearance((previous) => ({ ...previous, avatar }))
              }
            />

            <div className="space-y-6">
              <ProfileInput
                label="Display Name"
                value={displayName}
                onChange={setDisplayName}
                placeholder="Enter your display name"
              />

              <label className="block space-y-2">
                <span className="block text-sm font-semibold text-gray-200">
                  About Me
                </span>

                <textarea
                  value={bio}
                  onChange={(event) => setBio(event.target.value)}
                  rows={5}
                  placeholder="Tell the QuestLog community about yourself..."
                  className="w-full resize-y rounded-xl border border-gray-600 bg-[#0F172A] px-4 py-3 text-white outline-none transition focus:border-indigo-400"
                />
              </label>

              <ProfileInput
                label="BoardGameGeek Username"
                value={bggUsername}
                onChange={setBggUsername}
                placeholder="Your BGG username (optional)"
                maxLength={100}
              />
            </div>

            {error && (
              <p
                role="alert"
                className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-300"
              >
                {error}
              </p>
            )}

            <div className="flex flex-wrap justify-end gap-4 border-t border-gray-700 pt-6">
              <Link
                href="/profile"
                className="rounded-xl bg-gray-700 px-6 py-3 font-semibold transition hover:bg-gray-600"
              >
                Cancel
              </Link>

              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 font-semibold transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Save className="h-5 w-5" />
                {saving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        </form>
      </motion.div>
    </main>
  );
}
