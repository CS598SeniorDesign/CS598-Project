"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useParams } from "next/navigation";

interface GameAttribute {
  bgg_id: number;
  name: string;
}

interface GameDetails {
  bgg_id: number;
  primary_name: string;
  description: string | null;
  year_published: number | null;
  minimum_players: number | null;
  maximum_players: number | null;
  playing_time: number | null;
  minimum_playtime: number | null;
  maximum_playtime: number | null;
  minimum_age: number | null;
  thumbnail_url: string | null;
  image_url: string | null;
  average_rating: number | string | null;
  bgg_rank: number | null;
  categories: GameAttribute[];
  mechanics: GameAttribute[];
  publishers: GameAttribute[];
  designers: GameAttribute[];
  artists: GameAttribute[];
  families: GameAttribute[];
}

function getGameError(status: number): string {
  if (status === 401 || status === 403) {
    return "please log in to view game details.";
  }

  if (status === 404) {
    return "This game could not be found.";
  }

  return "Unable to load game details. Please try again.";
}

async function fetchGame(
  id: string,
  signal: AbortSignal,
): Promise<GameDetails> {
  const response = await fetch(`/api/v1/games/${encodeURIComponent(id)}/`, {
    credentials: "same-origin",
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error(getGameError(response.status));
  }

  return (await response.json()) as GameDetails;
}

function GameImage({ game }: { game: GameDetails }) {
  const imageUrl = game.image_url || game.thumbnail_url;

  if (!imageUrl) {
    return (
      <div className="flex h-80 items-center justify-center rounded-2xl bg-slate-800 text-gray-400">
        No image available
      </div>
    );
  }

  return (
    <div className="relative mx-auto h-96 w-full">
      <Image
        src={imageUrl}
        alt={`${game.primary_name} cover`}
        fill
        unoptimized
        sizes="(max-width: 1024px) 100vw, 320px"
        className="rounded-2xl object-contain"
      />
    </div>
  );
}

function GameTags({ title, items }: { title: string; items: GameAttribute[] }) {
  if (!items?.length) return null;

  return (
    <section className="mt-6">
      <h2 className="mb-3 text-xl font-semibold">{title}</h2>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <span
            key={item.bgg_id}
            className="rounded-full bg-indigo-600 px-3 py-1 text-sm"
          >
            {item.name}
          </span>
        ))}
      </div>
    </section>
  );
}

function GameInformation({ game }: { game: GameDetails }) {
  return (
    <div className="grid grid-cols-2 gap-4 rounded-2xl bg-gray-900 p-6 sm:grid-cols-3">
      <div>
        <p className="text-sm text-gray-400">Players</p>
        <p className="font-semibold">
          {game.minimum_players ?? "?"}–{game.maximum_players ?? "?"}
        </p>
      </div>

      <div>
        <p className="text-sm text-gray-400">Playing Time</p>
        <p className="font-semibold">
          {game.playing_time != null
            ? `${game.playing_time} minutes`
            : "Unknown"}
        </p>
      </div>

      <div>
        <p className="text-sm text-gray-400">Minimum Age</p>
        <p className="font-semibold">
          {game.minimum_age != null ? `${game.minimum_age}+` : "Unknown"}
        </p>
      </div>

      <div>
        <p className="text-sm text-gray-400">Published</p>
        <p className="font-semibold">{game.year_published ?? "Unknown"}</p>
      </div>

      <div>
        <p className="text-sm text-gray-400">BGG Rating</p>
        <p className="font-semibold">
          {game.average_rating != null
            ? Number(game.average_rating).toFixed(1)
            : "Not rated"}
        </p>
      </div>

      <div>
        <p className="text-sm text-gray-400">BGG Rank</p>
        <p className="font-semibold">{game.bgg_rank ?? "Unranked"}</p>
      </div>
    </div>
  );
}

function GameContent({ game }: { game: GameDetails }) {
  return (
    <>
      <Link
        href="/games/search"
        className="mb-6 inline-block text-indigo-400 hover:text-indigo-300"
      >
        ← Back to Game Search
      </Link>

      <div className="grid gap-8 lg:grid-cols-[320px_1fr]">
        <div>
          <GameImage game={game} />
        </div>

        <div>
          <h1 className="mb-2 text-3xl font-bold">{game.primary_name}</h1>

          <p className="mb-6 text-gray-400">BoardGameGeek ID: {game.bgg_id}</p>

          <GameInformation game={game} />

          <GameTags title="Categories" items={game.categories} />
          <GameTags title="Mechanics" items={game.mechanics} />

          <button
            type="button"
            disabled
            title="Play logging will be available after the backend integration."
            className="mt-8 cursor-not-allowed rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white opacity-60"
          >
            Log Play (Coming Soon)
          </button>
        </div>
      </div>

      {game.description && (
        <section className="mt-10 rounded-2xl bg-gray-900 p-6">
          <h2 className="mb-4 text-2xl font-semibold">About This Game</h2>
          <p className="whitespace-pre-line leading-7 text-gray-300">
            {game.description}
          </p>
        </section>
      )}

      <GameTags title="Publishers" items={game.publishers} />
      <GameTags title="Designers" items={game.designers} />
    </>
  );
}

export default function GameDetailsPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [game, setGame] = useState<GameDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadGame() {
      setLoading(true);
      setError("");

      try {
        const result = await fetchGame(id, controller.signal);

        if (!controller.signal.aborted) {
          setGame(result);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

        setGame(null);
        setError(err instanceof Error ? err.message : "Something went wrong.");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadGame();

    return () => controller.abort();
  }, [id]);

  return (
    <main className="min-h-screen bg-[#0F172A] p-8 text-[#F8FAFC]">
      {loading ? (
        <p className="mt-10 text-center text-gray-400">
          Loading game details...
        </p>
      ) : error ? (
        <p role="alert" className="mt-10 text-center text-red-400">
          {error}
        </p>
      ) : game ? (
        <GameContent game={game} />
      ) : (
        <p className="mt-10 text-center text-gray-400">Game not found.</p>
      )}
    </main>
  );
}
