"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";

const AVATARS = [
  "/avatars/avatar1.webp",
  "/avatars/avatar2.webp",
  "/avatars/avatar3.webp",
  "/avatars/avatar4.webp",
  "/avatars/avatar5.webp",
  "/avatars/avatar6.webp",
  "/avatars/avatar7.webp",
  "/avatars/avatar8.webp",
  "/avatars/avatar9.webp",
  "/avatars/avatar10.webp",
  "/avatars/avatar11.webp",
  "/avatars/avatar12.webp",
];

type OwnProfile = {
  user_id: string;
  avatar: string;
};

function getCsrfToken(): string {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith("csrf_token="));

  return cookie
    ? decodeURIComponent(cookie.substring("csrf_token=".length))
    : "";
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function getValidAvatar(avatar: string): string {
  return AVATARS.includes(avatar) ? avatar : "";
}

function getProfileRequestError(status: number): string {
  if (status === 401 || status === 403) {
    return "Please log in to select your avatar.";
  }

  return "Unable to load your profile.";
}

async function fetchOwnProfile(signal: AbortSignal): Promise<OwnProfile> {
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
    throw new Error(getProfileRequestError(response.status));
  }

  return (await response.json()) as OwnProfile;
}

async function getAvatarSaveError(response: Response): Promise<string> {
  if (response.status === 401 || response.status === 403) {
    return "Your session has expired. Please log in again.";
  }

  const details: unknown = await response.json().catch(() => null);

  if (details && typeof details === "object") {
    const fields = details as Record<string, unknown>;
    const avatarError = fields.avatar;

    if (Array.isArray(avatarError)) {
      const firstError: unknown = avatarError[0];

      if (typeof firstError === "string") {
        return firstError;
      }
    }
  }

  return "Unable to save your avatar. Please try again.";
}

async function saveAvatar(selectedAvatar: string): Promise<OwnProfile> {
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
      avatar: selectedAvatar,
    }),
  });

  if (!response.ok) {
    throw new Error(await getAvatarSaveError(response));
  }

  const updatedProfile = (await response.json()) as OwnProfile;

  if (!getValidAvatar(updatedProfile.avatar)) {
    throw new Error("The server did not return a valid saved avatar.");
  }

  return updatedProfile;
}

function updateLocalAvatar(avatar: string): void {
  localStorage.setItem("userAvatar", avatar);

  try {
    const savedProfile = localStorage.getItem("userProfile");

    const existingProfile: Record<string, unknown> = savedProfile
      ? (JSON.parse(savedProfile) as Record<string, unknown>)
      : {};

    localStorage.setItem(
      "userProfile",
      JSON.stringify({
        ...existingProfile,
        avatar,
      }),
    );
  } catch {
    // Django has already saved the avatar successfully.
  }
}

export default function AvatarSelectionPage() {
  const router = useRouter();

  const [selectedAvatar, setSelectedAvatar] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    fetchOwnProfile(controller.signal)
      .then((profile) => {
        if (!controller.signal.aborted) {
          setSelectedAvatar(getValidAvatar(profile.avatar));
        }
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) {
          setError(getErrorMessage(err, "Unable to load your profile."));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, []);

  async function handleConfirm(): Promise<void> {
    if (!selectedAvatar || saving || loading) {
      return;
    }

    setSaving(true);
    setError("");

    try {
      const updatedProfile = await saveAvatar(selectedAvatar);
      updateLocalAvatar(updatedProfile.avatar);
      router.push("/dashboardPpt");
    } catch (err) {
      setError(getErrorMessage(err, "Unable to save your avatar."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white p-4">
      <div className="w-full max-w-md bg-gray-900 p-8 rounded-xl">
        <h1 className="text-3xl font-bold mb-3">Pick Your Avatar</h1>

        <p className="text-gray-400 mb-6">
          Choose an avatar for your QuestLog profile. Your friends will be able
          to see it.
        </p>

        {loading ? (
          <p className="text-gray-400 mb-6">Loading your profile...</p>
        ) : (
          <div className="grid grid-cols-2 gap-4 mb-6">
            {AVATARS.map((avatar) => (
              <button
                key={avatar}
                type="button"
                onClick={() => {
                  setSelectedAvatar(avatar);
                  setError("");
                }}
                disabled={saving}
                aria-label={`Select ${avatar.split("/").pop()}`}
                aria-pressed={selectedAvatar === avatar}
                className="flex items-center justify-center rounded-lg p-2 disabled:opacity-50"
              >
                <Image
                  src={avatar}
                  alt="Avatar option"
                  width={80}
                  height={80}
                  className={`w-20 h-20 rounded-full object-cover border-4 ${
                    selectedAvatar === avatar
                      ? "border-indigo-500"
                      : "border-gray-700"
                  }`}
                />
              </button>
            ))}
          </div>
        )}

        {error && (
          <p role="alert" className="text-red-400 text-sm mb-4">
            {error}
          </p>
        )}

        <button
          type="button"
          onClick={() => void handleConfirm()}
          disabled={!selectedAvatar || saving || loading}
          className="bg-primary py-2 rounded-lg hover:opacity-90 w-full disabled:opacity-50"
        >
          {saving ? "Saving Avatar..." : "Confirm → Dashboard"}
        </button>
      </div>
    </div>
  );
}
