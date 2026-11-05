"use client";

import Image, { type StaticImageData } from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useEffect, useState, useSyncExternalStore } from "react";

// Avatars
import brandonAvatar from "@/public/avatars/brandon.webp";
import sydneyAvatar from "@/public/avatars/sydney.webp";
import jenniferAvatar from "@/public/avatars/jennifer.webp";
import supriyaAvatar from "@/public/avatars/supriya.webp";

// Game images
import terraformImg from "@/public/images/terraforming.webp";
import catanImg from "@/public/images/catan.webp";
import everdellImg from "@/public/images/everdell.webp";
import botanyImg from "@/public/images/botany.webp";

type BaseGame = {
  gameName: string;
  gameImg: string | StaticImageData;
};

type GameResult = BaseGame & {
  gameResult: "Won" | "Lost";
};

type Game = BaseGame;

type Play = GameResult & {
  playerCount: number;
  playDuration: string;
  playDate: string;
};

type CommunityItem = GameResult & {
  user: string;
  timeAgo: string;
  avatar?: string | StaticImageData;
};

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const games: Game[] = [
  { gameName: "Botany", gameImg: "/images/botany.webp" },
  { gameName: "Stardew Valley", gameImg: "/images/stardew.webp" },
  { gameName: "Pandemic", gameImg: "/images/pandemic.webp" },
  { gameName: "Root", gameImg: "/images/root.webp" },
  { gameName: "Catan", gameImg: "/images/catan.webp" },
];

const recentPlays: Play[] = [
  {
    gameName: "Terraforming Mars",
    gameImg: "/images/terraforming.webp",
    gameResult: "Won",
    playerCount: 2,
    playDuration: "90 min",
    playDate: "Feb 22",
  },
  {
    gameName: "Catan",
    gameImg: "/images/catan.webp",
    gameResult: "Lost",
    playerCount: 4,
    playDuration: "60 min",
    playDate: "March 11",
  },
  {
    gameName: "Azul",
    gameImg: "/images/azul.webp",
    gameResult: "Won",
    playerCount: 3,
    playDuration: "30 min",
    playDate: "January 21",
  },
];

const community: CommunityItem[] = [
  {
    user: "Brandon",
    timeAgo: "2hrs ago",
    gameResult: "Won",
    avatar: brandonAvatar,
    gameName: "Terraforming Mars",
    gameImg: terraformImg,
  },
  {
    user: "Sydney",
    timeAgo: "5hrs ago",
    gameResult: "Lost",
    avatar: sydneyAvatar,
    gameName: "Catan",
    gameImg: catanImg,
  },
  {
    user: "Jennifer",
    timeAgo: "1d ago",
    gameResult: "Won",
    avatar: jenniferAvatar,
    gameName: "Everdell",
    gameImg: everdellImg,
  },
  {
    user: "Supriya",
    timeAgo: "2d ago",
    gameResult: "Lost",
    avatar: supriyaAvatar,
    gameName: "Botany",
    gameImg: botanyImg,
  },
];

function subscribeToUserAvatar() {
  return () => {};
}

function getUserAvatarSnapshot() {
  return localStorage.getItem("userAvatar");
}

function getUserAvatarServerSnapshot() {
  return null;
}

export default function Page() {
  const router = useRouter();

  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [profileLoading, setProfileLoading] = useState(true);

  const userAvatar = useSyncExternalStore(
    subscribeToUserAvatar,
    getUserAvatarSnapshot,
    getUserAvatarServerSnapshot,
  );

  // Load the signed-in user's actual profile
  useEffect(() => {
    const controller = new AbortController();

    async function loadProfile() {
      try {
        const response = await fetch("/api/v1/profile/", {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error("Unable to load profile.");
        }

        const data: unknown = await response.json();

        if (
          typeof data === "object" &&
          data !== null &&
          "display_name" in data &&
          typeof data.display_name === "string"
        ) {
          if (!controller.signal.aborted) {
            setDisplayName(data.display_name);
          }
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          console.error("Unable to load dashboard profile:", error);
        }
      } finally {
        if (!controller.signal.aborted) {
          setProfileLoading(false);
        }
      }
    }

    void loadProfile();

    return () => controller.abort();
  }, []);

  async function handleLogout() {
    if (isLoggingOut) return;

    setIsLoggingOut(true);
    setLogoutError("");

    try {
      const cookie = document.cookie
        .split("; ")
        .find((item) => item.startsWith("csrf_token="));

      const csrfToken = cookie
        ? decodeURIComponent(cookie.substring("csrf_token=".length))
        : null;

      if (!csrfToken) {
        throw new Error(
          "Missing security token. Please refresh and try again.",
        );
      }

      const response = await fetch("/_allauth/browser/v1/auth/session", {
        method: "DELETE",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken,
        },
      });

      if (!response.ok && response.status !== 401) {
        throw new Error("Unable to log out. Please try again.");
      }

      router.replace("/login");
      router.refresh();
    } catch (error) {
      setLogoutError(
        error instanceof Error
          ? error.message
          : "Something went wrong while logging out.",
      );
    } finally {
      setIsLoggingOut(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0F172A] text-[#F8FAFC]">
      {/* NAVBAR */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-gradient-to-r from-[#1E293B] to-[#0F172A] px-4 py-4 shadow-xl sm:px-8">
        <h1 className="text-xl font-bold">QuestLog</h1>

        <nav
          aria-label="Dashboard navigation"
          className="flex flex-wrap items-center gap-4 text-gray-300 lg:gap-10"
        >
          <Link
            href="/library"
            className="border-b-2 border-[#4F46E5] pb-1 transition hover:text-white"
          >
            Game Library
          </Link>

          <Link href="/games/search" className="transition hover:text-white">
            Recommendations for you
          </Link>

          <Link href="/community" className="transition hover:text-white">
            Weeple
          </Link>

          <Link href="/analytics" className="transition hover:text-white">
            Your Analytics
          </Link>
        </nav>

        {/* Clickable user profile */}
        <div className="flex items-center gap-3">
          <Link
            href="/profile"
            className="flex items-center gap-3 rounded-lg p-1 transition hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400"
            aria-label="View your profile"
          >
            {userAvatar ? (
              <Image
                src={userAvatar}
                alt="User Avatar"
                width={32}
                height={32}
                className="h-8 w-8 rounded-full object-cover"
              />
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold text-white">
                {displayName.trim().charAt(0).toUpperCase() || "?"}
              </div>
            )}

            <span className="max-w-36 truncate text-sm font-medium text-white">
              {profileLoading
                ? "Loading..."
                : displayName.trim() || "My Profile"}
            </span>
          </Link>

          <button
            type="button"
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {isLoggingOut ? "Logging Out..." : "Log Out"}
          </button>
        </div>
      </div>

      {logoutError && (
        <p role="alert" className="px-8 pt-3 text-sm text-red-400">
          {logoutError}
        </p>
      )}

      <div className="p-4 sm:p-8">
        {/* TITLE */}
        <h1 className="text-4xl font-extrabold tracking-tight text-white">
          Welcome to QuestLog
        </h1>

        <p className="mb-6 text-gray-400">Your shared activity hub</p>

        {/* TOP ROW */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* RECENTLY PLAYED */}
          <div className="rounded-2xl bg-[#1E293B]/70 p-5 shadow-lg transition duration-300 hover:shadow-xl hover:shadow-indigo-500/10 lg:col-span-2">
            <h2 className="mb-4 text-gray-300">Recently Played</h2>

            <div className="flex gap-5 overflow-x-auto pb-2">
              {games.map((game) => (
                <Link
                  key={game.gameName}
                  href="/games/search"
                  className="block shrink-0"
                >
                  <div className="w-36 cursor-pointer sm:w-44">
                    <Image
                      src={game.gameImg}
                      alt={game.gameName}
                      width={200}
                      height={160}
                      className="mb-2 h-40 w-full rounded-xl object-cover transition duration-300 hover:scale-105 hover:shadow-[0_0_20px_rgba(79,70,229,0.4)]"
                    />

                    <p className="text-sm font-semibold">{game.gameName}</p>

                    <div className="text-sm text-[#FFBF00]">★★★★★</div>
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* CALENDAR */}
          <div className="rounded-2xl bg-[#1E293B]/70 p-5 shadow-lg transition duration-300 hover:shadow-xl hover:shadow-indigo-500/10">
            <h2 className="mb-2 text-gray-300">Calendar</h2>

            <h3 className="mb-3 text-center font-semibold tracking-wide">
              FEBRUARY
            </h3>

            <div className="mb-2 grid grid-cols-7 text-center text-xs text-gray-400">
              {days.map((day) => (
                <div key={day}>{day}</div>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-2 text-center text-sm">
              {Array.from({ length: 31 }, (_, index) => (
                <div
                  key={index}
                  className="relative flex h-10 items-center justify-center rounded-lg bg-[#0F172A] transition hover:bg-[#4F46E5]"
                >
                  {index + 1}

                  {(index === 9 || index === 22) && (
                    <div className="absolute bottom-1 rounded bg-[#10B981] px-2 text-[10px] text-indigo-300">
                      Game
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* MIDDLE ROW */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* RECENT PLAYS */}
          <div className="rounded-2xl bg-[#1E293B]/70 p-5 shadow-lg transition duration-300 hover:shadow-xl hover:shadow-indigo-500/10">
            <h2 className="mb-3">Recent Plays</h2>

            {recentPlays.map((play) => (
              <div
                key={`${play.gameName}-${play.playDate}`}
                className="mb-2 flex gap-3 rounded-lg bg-[#0F172A] p-3"
              >
                <Image
                  src={play.gameImg}
                  alt={play.gameName}
                  width={48}
                  height={48}
                  className="h-12 w-12 rounded-lg object-cover"
                />

                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{play.gameName}</p>

                  <p className="text-xs text-gray-400">
                    {play.playDate} | {play.playerCount} Players |{" "}
                    {play.playDuration}
                  </p>
                </div>

                <span
                  className={`text-sm font-semibold ${
                    play.gameResult === "Won"
                      ? "text-[#10B981]"
                      : "text-[#EF4444]"
                  }`}
                >
                  {play.gameResult}
                </span>
              </div>
            ))}
          </div>

          {/* COMMUNITY */}
          <div className="rounded-2xl bg-[#1E293B]/70 p-5 shadow-lg transition duration-300 hover:shadow-xl hover:shadow-indigo-500/10">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2>Weeple Community Feed</h2>

              <Link
                href="/community"
                className="text-sm font-medium text-indigo-400 transition hover:text-indigo-300 hover:underline"
              >
                View Community →
              </Link>
            </div>

            {community.map((item) => (
              <div
                key={`${item.user}-${item.gameName}`}
                className="mb-2 flex items-center gap-3 rounded-lg bg-[#0F172A] p-2"
              >
                <Image
                  src={item.avatar!}
                  alt={item.user}
                  width={40}
                  height={40}
                  className="h-10 w-10 rounded-full object-cover"
                />

                <Image
                  src={item.gameImg}
                  alt={item.gameName}
                  width={50}
                  height={50}
                  className="rounded-lg object-cover"
                />

                <div className="flex flex-col">
                  <span className="text-sm font-semibold">
                    {item.user} • {item.timeAgo}
                  </span>

                  <span className="text-xs text-gray-400">
                    Played {item.gameName}
                  </span>
                </div>

                <span
                  className={`ml-auto rounded px-2 py-1 text-xs font-semibold ${
                    item.gameResult === "Won"
                      ? "bg-green-600 text-white"
                      : "bg-red-600 text-white"
                  }`}
                >
                  {item.gameResult}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* BOTTOM ROW */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* MEMBERS */}
          <div className="rounded-2xl bg-[#1E293B]/70 p-5 shadow-lg transition duration-300 hover:shadow-xl hover:shadow-indigo-500/10">
            <h2 className="mb-3">Members</h2>

            {["Brandon", "Jennifer", "Sydney", "Supriya"].map((member) => (
              <div
                key={member}
                className="mb-2 flex justify-between rounded-lg bg-[#0F172A] p-2"
              >
                <span>{member}</span>

                <span className="text-xs text-[#FFBF00]">Tag</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
