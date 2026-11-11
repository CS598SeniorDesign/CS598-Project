"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Gamepad2, ShieldCheck, UserRound } from "lucide-react";

type Friend = {
  user_id: string;
  display_name: string;
  avatar?: string | null;
};

const DEFAULT_AVATAR = "/avatars/avatar1.webp";

const ALLOWED_AVATARS = new Set([
  "/avatars/brandon.webp",
  "/avatars/sydney.webp",
  "/avatars/jennifer.webp",
  "/avatars/supriya.webp",
  "/avatars/avatar1.webp",
  "/avatars/avatar2.webp",
  "/avatars/avatar3.webp",
  "/avatars/avatar4.webp",
  "/avatars/avatar5.webp",
]);

function getAvatar(avatar?: string | null): string {
  return avatar && ALLOWED_AVATARS.has(avatar) ? avatar : DEFAULT_AVATAR;
}

function isFriend(value: unknown): value is Friend {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  if (!("user_id" in value) || typeof value.user_id !== "string") {
    return false;
  }

  if (!("display_name" in value) || typeof value.display_name !== "string") {
    return false;
  }

  return (
    !("avatar" in value) ||
    value.avatar === null ||
    typeof value.avatar === "string"
  );
}

async function fetchFriend(
  userId: string,
  signal: AbortSignal,
): Promise<Friend | null> {
  const response = await fetch("/api/v1/friends/", {
    credentials: "same-origin",
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error(
      response.status === 401 || response.status === 403
        ? "Please log in to view friends."
        : "Unable to load your friends.",
    );
  }

  const data: unknown = await response.json();

  if (!Array.isArray(data) || !data.every(isFriend)) {
    throw new Error("Unexpected friends response.");
  }

  return data.find((friend: Friend) => friend.user_id === userId) ?? null;
}

export default function FriendProfilePage() {
  const { userId } = useParams<{ userId: string }>();

  const [friend, setFriend] = useState<Friend | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setLoading(true);
      setError("");
      setFriend(null);

      try {
        const result = await fetchFriend(userId, controller.signal);

        if (!controller.signal.aborted) {
          setFriend(result);
        }
      } catch (caughtError) {
        if (!controller.signal.aborted) {
          setError(
            caughtError instanceof Error
              ? caughtError.message
              : "Unable to load this profile.",
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => controller.abort();
  }, [userId]);

  return (
    <main className="min-h-screen bg-[#0F172A] px-4 py-8 text-[#F8FAFC] sm:px-8">
      <div className="mx-auto max-w-5xl">
        <Link
          href="/community"
          className="mb-8 inline-flex items-center gap-2 text-sm font-semibold text-indigo-300 transition hover:text-indigo-200"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Community
        </Link>

        {loading && (
          <p role="status" className="text-gray-300">
            Loading player profile...
          </p>
        )}

        {!loading && error && (
          <div
            role="alert"
            className="rounded-xl border border-red-700 bg-red-950/40 p-5 text-red-300"
          >
            {error}
          </div>
        )}

        {!loading && !error && !friend && (
          <div className="rounded-xl border border-gray-700 bg-[#1E293B] p-8">
            <h1 className="text-2xl font-bold">Profile unavailable</h1>

            <p className="mt-3 text-gray-400">
              This player is not available in your friends list.
            </p>
          </div>
        )}

        {!loading && !error && friend && (
          <>
            <div className="mb-6">
              <h1 className="text-3xl font-bold">Player Profile</h1>

              <p className="mt-2 text-sm text-gray-400">
                Get to know your QuestLog friends.
              </p>
            </div>

            <section className="overflow-hidden rounded-2xl border border-gray-700 bg-[#1E293B] shadow-xl">
              <div className="h-52 bg-gradient-to-r from-indigo-900 via-indigo-700 to-emerald-700 sm:h-64" />

              <div className="relative px-6 pb-8 sm:px-10">
                <div className="-mt-14 mb-4">
                  <Image
                    src={getAvatar(friend.avatar)}
                    alt={`${friend.display_name}'s avatar`}
                    width={128}
                    height={128}
                    className="h-28 w-28 rounded-full border-4 border-[#1E293B] bg-indigo-600 object-cover shadow-lg sm:h-32 sm:w-32"
                  />
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-2xl font-bold">{friend.display_name}</h2>

                  <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-200">
                    <ShieldCheck className="h-4 w-4" />
                    Friends
                  </span>
                </div>

                <p className="mt-3 text-gray-400">
                  This player&apos;s bio and additional profile details will
                  appear here when public profile viewing is connected.
                </p>
              </div>
            </section>

            <section className="mt-8 rounded-2xl border border-gray-700 bg-[#1E293B] p-6">
              <div className="mb-4 flex items-center gap-2">
                <UserRound className="h-6 w-6 text-indigo-400" />

                <h2 className="text-xl font-bold">About This Player</h2>
              </div>

              <p className="text-sm leading-relaxed text-gray-400">
                More profile information is coming soon.
              </p>
            </section>

            <section className="mt-8 rounded-2xl border border-gray-700 bg-[#1E293B] p-6">
              <div className="mb-4 flex items-center gap-2">
                <Gamepad2 className="h-6 w-6 text-indigo-400" />

                <h2 className="text-xl font-bold">Gaming Stats</h2>
              </div>

              <div className="rounded-xl border border-dashed border-gray-600 bg-[#0F172A]/60 p-8 text-center">
                <p className="text-gray-300">
                  Player statistics are not available yet.
                </p>

                <p className="mt-2 text-sm text-gray-400">
                  Games played, wins, and recent activity can be displayed here
                  once the player stats API is connected.
                </p>
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
