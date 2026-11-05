"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  BookOpen,
  CalendarDays,
  Gamepad2,
  Settings,
  Trophy,
  Users,
  Pencil,
  Clock3,
  ArrowRight,
} from "lucide-react";

type UserProfile = {
  user_id: string;
  display_name: string;
  bio: string;
  privacy_level: "PUBLIC" | "FRIENDS" | "PRIVATE";
  bgg_username: string;
};

type LocalProfile = {
  avatar?: string;
  cover?: string;
};

function getSavedAppearance(): LocalProfile {
  if (typeof window === "undefined") return {};

  let appearance: LocalProfile = {};

  try {
    const saved = localStorage.getItem("userProfile");

    if (saved) {
      appearance = JSON.parse(saved) as LocalProfile;
    }
  } catch {
    console.error("Unable to read saved profile appearance.");
  }

  try {
    return {
      avatar: localStorage.getItem("userAvatar") || appearance.avatar || "",
      cover: localStorage.getItem("userCover") || appearance.cover || "",
    };
  } catch {
    return appearance;
  }
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
        ? "Please log in to view your profile."
        : "Unable to load your profile.",
    );
  }

  return (await response.json()) as UserProfile;
}

function ProfileStatCard({
  title,
  icon: Icon,
  description,
}: {
  title: string;
  icon: typeof Gamepad2;
  description: string;
}) {
  return (
    <div className="rounded-2xl border border-gray-700 bg-[#1E293B] p-5 transition hover:border-indigo-500/50">
      <div className="mb-4 flex items-center justify-between">
        <div className="rounded-xl bg-indigo-500/10 p-3">
          <Icon className="h-6 w-6 text-indigo-400" />
        </div>
      </div>

      <p className="text-3xl font-bold text-white">—</p>

      <h3 className="mt-2 font-semibold text-gray-200">{title}</h3>

      <p className="mt-1 text-xs text-gray-400">{description}</p>
    </div>
  );
}

function PlayerStats() {
  return (
    <section className="mt-8">
      <div className="mb-5 flex items-center gap-2">
        <Gamepad2 className="h-6 w-6 text-indigo-400" />
        <h2 className="text-2xl font-bold">Player Stats</h2>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <ProfileStatCard
          title="Games in Library"
          icon={BookOpen}
          description="Your board game collection"
        />

        <ProfileStatCard
          title="Sessions Played"
          icon={CalendarDays}
          description="Logged game sessions"
        />

        <ProfileStatCard
          title="Games Won"
          icon={Trophy}
          description="Your victories"
        />

        <ProfileStatCard
          title="Friends"
          icon={Users}
          description="Your QuestLog connections"
        />
      </div>
    </section>
  );
}

function RecentActivity() {
  return (
    <section className="mt-8 rounded-2xl border border-gray-700 bg-[#1E293B] p-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Clock3 className="h-6 w-6 text-indigo-400" />

          <h2 className="text-xl font-bold">Recent Activity</h2>
        </div>

        <Link
          href="/dashboardPpt"
          className="inline-flex items-center gap-2 text-sm font-semibold text-indigo-400 transition hover:text-indigo-300"
        >
          View Dashboard
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-600 bg-[#0F172A]/60 px-5 py-12 text-center">
        <div className="mb-4 rounded-full bg-indigo-500/10 p-4">
          <Gamepad2 className="h-8 w-8 text-indigo-400" />
        </div>

        <h3 className="text-lg font-semibold text-white">
          Your gaming journey starts here!
        </h3>

        <p className="mt-2 max-w-md text-sm leading-relaxed text-gray-400">
          Your recently played games and logged sessions will appear here once
          activity tracking is connected.
        </p>

        <Link
          href="/dashboardPpt"
          className="mt-5 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold transition hover:bg-indigo-500"
        >
          <Gamepad2 className="h-4 w-4" />
          Go to Dashboard
        </Link>
      </div>
    </section>
  );
}

function ProfileHeader({
  profile,
  appearance,
}: {
  profile: UserProfile;
  appearance: LocalProfile;
}) {
  const displayName = profile.display_name || "QuestLog Player";
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-700 bg-[#1E293B] shadow-xl">
      {/* COVER */}
      <div className="relative h-52 overflow-hidden sm:h-64">
        {appearance.cover ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={appearance.cover}
            alt="Profile cover"
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="h-full w-full bg-gradient-to-r from-indigo-900 via-indigo-700 to-emerald-700" />
        )}
      </div>

      {/* PROFILE DETAILS */}
      <div className="relative px-6 pb-8 sm:px-10">
        <div className="-mt-14 mb-4 flex items-end justify-between">
          <div className="relative flex h-28 w-28 items-center justify-center overflow-hidden rounded-full border-4 border-[#1E293B] bg-indigo-600 text-4xl font-bold shadow-lg sm:h-32 sm:w-32">
            {appearance.avatar ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={appearance.avatar}
                alt={`${displayName}'s avatar`}
                className="h-full w-full object-cover"
              />
            ) : (
              <span>{initial}</span>
            )}
          </div>
        </div>

        <h2 className="text-2xl font-bold">{displayName}</h2>

        <p className="mt-2 max-w-2xl whitespace-pre-wrap text-gray-300">
          {profile.bio || "Add a bio to introduce yourself to other players!"}
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <span className="rounded-full border border-indigo-500/40 bg-indigo-500/10 px-4 py-2 text-sm capitalize text-indigo-200">
            Privacy: {profile.privacy_level.toLowerCase()}
          </span>

          {profile.bgg_username && (
            <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-200">
              BGG: {profile.bgg_username}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [appearance, setAppearance] = useState<LocalProfile>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadProfile() {
      try {
        const data = await fetchOwnProfile(controller.signal);
        const savedAppearance = getSavedAppearance();

        if (controller.signal.aborted) return;

        setProfile(data);
        setAppearance(savedAppearance);
      } catch (err) {
        if (controller.signal.aborted) return;

        setError(err instanceof Error ? err.message : "Something went wrong.");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadProfile();

    return () => controller.abort();
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen bg-[#0F172A] p-8 text-white">
        <p className="text-gray-300">Loading your profile...</p>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="min-h-screen bg-[#0F172A] p-8 text-white">
        <h1 className="mb-4 text-3xl font-bold">Your Profile</h1>

        <p role="alert" className="mb-6 text-red-400">
          {error || "Your profile is unavailable."}
        </p>

        <Link
          href="/login"
          className="inline-block rounded-xl bg-indigo-600 px-5 py-2 hover:bg-indigo-500"
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
        className="mx-auto max-w-5xl"
      >
        {/* PAGE TITLE */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Your Profile</h1>

            <p className="mt-1 text-sm text-gray-400">
              Your personal space in the QuestLog community.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              href="/profile/edit"
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold transition hover:bg-indigo-500"
            >
              <Pencil className="h-4 w-4" />
              Edit Profile
            </Link>

            <Link
              href="/settings"
              className="inline-flex items-center gap-2 rounded-xl border border-gray-600 bg-gray-800 px-5 py-2.5 text-sm font-semibold transition hover:bg-gray-700"
            >
              <Settings className="h-4 w-4" />
              Settings
            </Link>
          </div>
        </div>

        <ProfileHeader profile={profile} appearance={appearance} />

        <PlayerStats />

        <RecentActivity />
      </motion.div>
    </main>
  );
}
