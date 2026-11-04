"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

type Friend = {
  user_id: number;
  display_name: string;
};

export default function FriendsList() {
  const [friends, setFriends] = useState<Friend[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadFriends() {
      try {
        const response = await fetch("/api/v1/friends/", {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          signal: controller.signal,
        });

        if (response.status === 401 || response.status === 403) {
          throw new Error("Please log in to view your friends.");
        }

        if (!response.ok) {
          throw new Error("Unable to load your friends right now.");
        }

        const data: unknown = await response.json();

        if (!Array.isArray(data)) {
          throw new Error("Unexpected friends response.");
        }

        const validFriends: Friend[] = data.filter(
          (item): item is Friend =>
            typeof item === "object" &&
            item !== null &&
            typeof item.user_id === "number" &&
            typeof item.display_name === "string",
        );

        if (!controller.signal.aborted) {
          setFriends(validFriends);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

        setError(
          err instanceof Error
            ? err.message
            : "Something went wrong loading your friends.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadFriends();

    return () => controller.abort();
  }, []);

  return (
    <section className="border-t border-gray-500 pt-6">
      <h2 className="mb-6 text-3xl font-bold tracking-wide">YOUR FRIENDS</h2>

      {loading && <p className="text-gray-400">Loading your friends...</p>}

      {!loading && error && (
        <p role="alert" className="text-red-400">
          {error}
        </p>
      )}

      {!loading && !error && friends.length === 0 && (
        <div className="rounded-xl border border-gray-700 bg-slate-800/40 p-5">
          <p className="text-lg font-medium">No friends yet</p>
          <p className="mt-2 text-sm text-gray-400">
            Your QuestLog friends will appear here once you connect with other
            players.
          </p>
        </div>
      )}

      {!loading && !error && friends.length > 0 && (
        <ul className="space-y-6">
          {friends.map((friend) => (
            <li
              key={friend.user_id}
              className="flex items-center gap-4 text-xl sm:text-2xl"
            >
              <Image
                src="/avatars/avatar1.webp"
                alt=""
                width={56}
                height={56}
                className="h-14 w-14 rounded-full border border-gray-500 object-cover"
              />

              <span className="font-medium">{friend.display_name}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
