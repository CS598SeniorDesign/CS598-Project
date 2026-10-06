"use client";

import Image from "next/image";
import { useState } from "react";


const libraryGames = [
  { name: "Root", image: "/images/root.webp", rating: 4 },
  { name: "Munchkin", image: "/images/munchkin.webp", rating: 5 },
  { name: "Pandemic", image: "/images/pandemic.webp", rating: 4 },
  { name: "Catan", image: "/images/catan.webp", rating: 5 },
  { name: "The Hunger Games", image: "/images/hungergames.webp", rating: 5 },
  { name: "Wingspan", image: "/images/wingspan.webp", rating: 5 },
  { name: "Clue", image: "/images/clue.webp", rating: 3 },
  { name: "Sorry", image: "/images/sorry.webp", rating: 4 },
  { name: "Uno", image: "/images/uno.webp", rating: 4 },
  { name: "Monopoly", image: "/images/monopoly.webp", rating: 4 },
  { name: "Azul", image: "/images/azul.webp", rating: 5 },
  { name: "Terraforming Mars", image: "/images/terraforming.webp", rating: 5 },
  { name: "Betrayal at House on the Hill", image: "/images/betrayal.webp", rating: 4 },
  { name: "Botany", image: "/images/botany.webp", rating: 4 },
  { name: "Stardew Valley", image: "/images/stardew.webp", rating: 3 },
  { name: "Life in Reterra", image: "/images/lifeinreterra.webp", rating: 5 },
  { name: "Everdell", image: "/images/everdell.webp", rating: 3 },
  { name: "Spirit Island", image: "/images/spiritIsland.webp", rating: 5 },
  { name: "The Sims", image: "/images/sims.webp", rating: 4 },
  { name: "Fallout", image: "/images/fallout.webp", rating: 4 },
  { name: "Command of Nature", image: "/images/command.webp", rating: 4 },
  { name: "Lairs", image: "/images/lairs.webp", rating: 3 },
  { name: "Excursions", image: "/images/excursions.webp", rating: 2 },
  { name: "The Lord of the Rings", image: "/images/lordofrings.webp", rating: 4 },
];

export default function LibraryPage() {
  const [query, setQuery] = useState("");

  const filteredGames = libraryGames.filter((game) =>
    game.name.toLowerCase().includes(query.trim().toLowerCase())
  );
  return (
    <div className="min-h-screen bg-[#0F172A] px-8 py-10 text-white">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-5xl font-black tracking-widest">LIBRARY</h1>
          <p className="mt-2 text-gray-400">
            Board games in your QuestLog collection
          </p>
        </div>

        <button className="rounded-full bg-[#F87171] px-8 py-3 text-sm font-bold uppercase tracking-wider text-black hover:bg-[#FB7185] transition">
          Wishlist
        </button>
      </div>

      {/* SEARCH */}
      <div className="mb-8 flex items-center gap-4">
        <input
          type="text"
          placeholder="Search your collection..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full max-w-md rounded-full border border-gray-700 bg-[#1E293B] px-5 py-3 outline-none focus:border-[#4F46E5]"
        />
      </div>

      {/* GRID */}
      {filteredGames.length > 0 ? (
        <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {filteredGames.map((game) => (
            <div
              key={game.name}
              className="rounded-2xl bg-[#1E293B]/70 p-3 transition hover:-translate-y-1 hover:shadow-xl hover:shadow-indigo-500/20"
            >
              <Image
                src={game.image}
                alt={game.name}
                width={220}
                height={280}
                className="h-64 w-full rounded-xl object-cover"
              />

              <h2 className="mt-3 text-center text-sm font-bold">
                {game.name}
              </h2>

              <div className="mt-2 text-center text-[#FACC15]">
                {"★".repeat(game.rating)}
                <span className="text-gray-600">
                  {"★".repeat(5 - game.rating)}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-center mt-10 text-gray-400">
          No games found 😢
        </p>
      )}
    </div>
  );
}