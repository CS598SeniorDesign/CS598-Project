"use client";

import { useState } from "react";

type Game = {
  name: string;
  type: string;
  players: string;
  image: string;
};

const games: Game[] = [
  {
    name: "Catan",
    type: "Strategy",
    players: "3–4",
    image: "/images/catan.webp",
  },
  {
    name: "Azul",
    type: "Abstract",
    players: "2–4",
    image: "/images/azul.webp",
  },
  {
    name: "Terraforming Mars",
    type: "Strategy",
    players: "1–5",
    image: "/images/terraforming.webp",
  },
  {
    name: "Wingspan",
    type: "Engine Builder",
    players: "1–5",
    image: "/images/wingspan.webp",
  },
    {
    name: "Pandemic",
    type: "Cooperative Strategy",
    players: "2-4",
    image: "/images/pandemic.webp",
  },
    {
    name: "Root",
    type: "Adventure and War",
    players: "2-4",
    image: "/images/root.webp",
  },
    {
    name: "Stardew",
    type: "Farming Simulation",
    players: "1–4",
    image: "/images/stardew.webp",
  },
    {
    name: "Boatny",
    type: "Adventure Strategy",
    players: "1–5",
    image: "/images/botany.webp",
  },
    {
    name: "Everdell",
    type: "Tableau Building",
    players: "1–5",
    image: "/images/everdell.webp",
  },
    {
    name: "Lords of Waterdeep",
    type: "Resource Management Strategy",
    players: "2-5",
    image: "/images/lordsofwaterdeep.webp",
  },
];

export default function Page() {
  const [query, setQuery] = useState<string>("");

  const filteredGames = games.filter((game) =>
    game.name.toLowerCase().includes(query.trim().toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[#0F172A] text-[#F8FAFC] p-8">

      <h1 className="text-3xl font-bold mb-2">
        Smart Game Search
      </h1>

      <p className="text-gray-400 mb-6">
        Powered by Elasticsearch + BGG API
      </p>

      <input
        type="text"
        placeholder="Try typing 'ca' or 'wi'..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full p-4 rounded-2xl bg-gray-900 border border-gray-700 mb-8 focus:outline-none focus:ring-2 focus:ring-[#4F46E5]"
      />

      {filteredGames.length > 0 ? (
        <div className="grid grid-cols-3 gap-6">
          {filteredGames.map((game) => (
            <div
              key={game.name}
              className="bg-gray-900 p-4 rounded-2xl shadow-lg hover:scale-105 hover:shadow-[#4F46E5]/20 transition"
            >
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