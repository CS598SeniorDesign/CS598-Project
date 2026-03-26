"use client";

import { useState } from "react";
import Link from "next/link";

type Game = {
  id: number;
  name: string;
  type: string;
  players: string;
  image: string;
};

const allGames: Game[] = [
  { id: 1, name: "Catan", type: "Strategy", players: "3–4", image: "/images/catan.webp" },
  { id: 2, name: "Azul", type: "Abstract", players: "2–4", image: "/images/azul.webp" },
  { id: 3, name: "Terraforming Mars", type: "Strategy", players: "1–5", image: "/images/terraforming.webp" },
  { id: 4, name: "Wingspan", type: "Engine Builder", players: "1–5", image: "/images/wingspan.webp" },
  { id: 5, name: "Pandemic", type: "Cooperative Strategy", players: "2–4", image: "/images/pandemic.webp" },
  { id: 6, name: "Root", type: "Adventure and War", players: "2–4", image: "/images/root.webp" },
  { id: 7, name: "Stardew", type: "Farming Simulation", players: "1–4", image: "/images/stardew.webp" },
  { id: 8, name: "Botany", type: "Adventure Strategy", players: "1–5", image: "/images/botany.webp" },
  { id: 9, name: "Everdell", type: "Tableau Building", players: "1–5", image: "/images/everdell.webp" },
  { id: 10, name: "Lords of Waterdeep", type: "Resource Management Strategy", players: "2–5", image: "/images/lordsofwaterdeep.webp" },
];

export default function Page() {
  const [query, setQuery] = useState("");

  const filteredGames = allGames.filter((game) =>
    game.name.toLowerCase().includes(query.trim().toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[#0F172A] text-[#F8FAFC] p-8">

      {/* TITLE */}
      <h1 className="text-3xl font-bold mb-2">
        Game Search
      </h1>

      <p className="text-gray-400 mb-6">
        Find your next favorite game 🎲
      </p>

      {/* SEARCH BAR */}
      <div className="flex gap-4 mb-8">
        <input
          type="text"
          placeholder="Search games..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full p-4 rounded-2xl bg-gray-900 border border-gray-700 focus:outline-none focus:ring-2 focus:ring-[#4F46E5]"
        />

        {/* optional button (future API ready) */}
        <button className="bg-[#4F46E5] px-6 rounded-xl hover:bg-indigo-500 transition">
          Search
        </button>
      </div>

      {/* RESULTS */}
      {filteredGames.length > 0 ? (
        <div className="grid grid-cols-3 gap-6">
          {filteredGames.map((game) => (
            <Link key={game.id} href={`/games/${game.name}`}>
              <div className="bg-gray-900 p-4 rounded-2xl shadow-lg cursor-pointer
                              transition duration-300 hover:scale-105 hover:shadow-indigo-500/20">

                <img
                  src={game.image}
                  alt={game.name}
                  className="rounded-lg mb-3 h-40 w-full object-cover"
                />

                <p className="font-semibold text-lg">{game.name}</p>
                <p className="text-sm text-gray-400">
                  {game.type} • {game.players} players
                </p>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <p className="text-center mt-10 text-gray-400">
          No results found 😢
        </p>
      )}
    </div>
  );
}