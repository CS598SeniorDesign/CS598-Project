"use client";
import Image from "next/image";
import { useState } from "react";
import Link from "next/link";
import WinRateChart from "@/components/stats/WinRateChart";
import CollapsiblePanel from "@/components/ui/CollapsiblePanel";
//for avatars
import brandonAvatar from "@/public/avatars/brandon.webp";
import sydneyAvatar from "@/public/avatars/sydney.webp";
import jenniferAvatar from "@/public/avatars/jennifer.webp";
import supriyaAvatar from "@/public/avatars/supriya.webp";

import { StaticImageData} from "next/image";

//for game images
import terraformImg from "@/public/images/terraforming.webp";
import catanImg from "@/public/images/catan.webp";
import everdellImg from "@/public/images/everdell.webp";
import botanyImg from "@/public/images/botany.webp";

export default function Page() {
  type Game = {
    name: string;
    img: string;
  };

  type Play = {
    name: string;
    img: string;
    result: "Won" | "Lost";
    players: number;
    time: string;
    date: string;
  };

  type CommunityItem = {
  name: string; // game name
  img: string | StaticImageData; // game image
  user: string;
  time: string;
  result: "Won" | "Lost";
  avatar?: string | StaticImageData;
};

  const games: Game[] = [
    { name: "Botany", img: "/images/botany.webp" },
    { name: "Stardew Valley", img: "/images/stardew.webp" },
    { name: "Pandemic", img: "/images/pandemic.webp" },
    { name: "Root", img: "/images/root.webp" },
    { name: "Catan", img: "/images/catan.webp"},
  ];

  const recentPlays: Play[] = [
    {
      name: "Terraforming Mars",
      img: "/images/terraforming.webp",
      result: "Won",
      players: 2,
      time: "90 min",
      date: "Feb 22",
    },
    {
      name: "Catan",
      img: "/images/catan.webp",
      result: "Lost",
      players: 4,
      time: "60 min",
      date: "March 11",
    },
    {
      name: "Azul",
      img: "/images/azul.webp",
      result: "Won",
      players: 3,
      time: "30 min",
      date: "January 21",
    },
  ];

 const community: CommunityItem[] = [
  { user: "Brandon", time: "2hrs ago", result: "Won", avatar: brandonAvatar, name: "Terraforming Mars", img: terraformImg },
  { user: "Sydney", time: "5hrs ago", result: "Lost", avatar: sydneyAvatar, name: "Catan", img: catanImg },
  { user: "Jennifer", time: "1d ago", result: "Won", avatar: jenniferAvatar, name: "Everdell", img: everdellImg },
  { user: "Supriya", time: "2d ago", result: "Lost", avatar: supriyaAvatar, name: "Botany", img: botanyImg },
];

  const days: string[] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
   
  const [openChart, setOpenChart] = useState<null | "winrate" | "donut">(null);
  
  // get the avatar saved by the user in Avatar Picker
const userAvatar =
  typeof window !== "undefined" ? localStorage.getItem("userAvatar") : null;

  return (
    <div className=" min-h-screen bg-[#0F172A] text-[#F8FAFC]">
      {/* NAVBAR */}
      <div className="flex justify-between items-center px-8 py-4 bg-gradient-to-r from-[#1E293B] to-[#0F172A] shadow-xl">
        <h1 className="text-xl font-bold">QuestLog</h1>

        <div className="flex gap-10 text-gray-300">
          <p className="border-b-2 border-[#4F46E5] pb-1 cursor-pointer">
            Game Library
          </p>
        <Link href="/games/search">
          <p className="hover:text-white cursor-pointer transition">
            Recommendations for you
          </p>
        </Link>
          <p className="hover:text-white cursor-pointer transition">
            Weeple
          </p>
        </div>

        <div className="flex items-center gap-3">
           {userAvatar ? (
            <img 
              src={userAvatar}
              alt="User Avatar"
              className="w-8 h-8 rounded-full object-cover"
              />
           ) : (
          <div className="w-8 h-8 bg-gray-500 rounded-full" />
           )}
          <p>MeepleTeam</p>
        </div>
      </div>
    
      <div className="p-8">
        {/* TITLE */}
        <h1 className="text-3xl font-bold">Welcome to QuestLog</h1>
        <p className="text-gray-400 mb-6">Your shared activity hub</p>

        {/* TOP ROW */}
        <div className="grid grid-cols-3 gap-6">
          {/* RECENT GROUP GAMES */}
          <div className="col-span-2 bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg transition duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-indigo-500/10">
            <h2 className="mb-4 text-gray-300">Recently Played</h2>

            <div className="flex gap-5">
              {games.map((game, i) => (
               <Link key={i} href={`/games/${game.name}`}>
                <div className="w-44 cursor-pointer">
                 <img
                  src={game.img}
                  className="rounded-xl mb-2 h-40 w-full object-cover transition duration-300 hover:scale-105 hover:shadow-[0_0_20px_rgba(79,70,229,0.4)]"
                 />
                   <p className="text-sm font-semibold">{game.name}</p>
                   <div className="text-[#FFBF00] text-sm">★★★★★</div>
               </div>
             </Link>
            ))}
          </div>
        </div>
          {/* CALENDAR */}
          <div className="bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg transition duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-indigo-500/10">
            <h2 className="mb-2 text-gray-300">Calendar</h2>
            <h3 className="text-center mb-3 font-semibold tracking-wide">
              FEBRUARY
            </h3>

            {/* Days */}
            <div className="grid grid-cols-7 text-xs text-gray-400 mb-2 text-center">
              {days.map((d) => (
                <div key={d}>{d}</div>
              ))}
            </div>

            {/* Dates */}
            <div className="grid grid-cols-7 gap-2 text-sm text-center">
              {[...Array(31)].map((_, i) => (
                <div
                  key={i}
                  className="h-10 flex items-center justify-center rounded-lg bg-[#0F172A] hover:bg-[#4F46E5] transition relative"
                >
                  {i + 1}

                  {(i === 9 || i === 22) && (
                    <div className="absolute bottom-1 text-[10px] bg-[#10B981] text-indigo-300 px-2 rounded">
                      Game
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* MIDDLE ROW */}
        <div className="grid grid-cols-3 gap-6 mt-6">
          {/* RECENT PLAYS */}
          <div className="bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg transition duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-indigo-500/10">
            <h2 className="mb-3">Recent Plays</h2>

            {recentPlays.map((play, i) => (
              <div
                key={i}
                className="flex gap-3 bg-[#0F172A] p-3 rounded-lg mb-2"
              >
                <img
                  src={play.img}
                  className="w-12 h-12 rounded-lg object-cover"
                />

                <div className="flex-1">
                  <p className="text-sm font-semibold">{play.name}</p>
                  <p className="text-xs text-gray-400">
                    {play.date} | {play.players} Players | {play.time}
                  </p>
                </div>

                <span
                  className={`text-sm font-semibold ${
                    play.result === "Won"
                      ? "text-[#10B981]"
                      : "text-[#EF4444]"
                  }`}
                >
                  {play.result}
                </span>
              </div>
            ))}
          </div>

          {/* COMMUNITY */}
          <div className="bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg transition duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-indigo-500/10">
            <h2 className="mb-3">Weeple Community Feed</h2>

            {community.map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-3 bg-[#0F172A] p-2 rounded-lg mb-2"
              >
                 {/* Avatar */}
                  <Image
                  src={item.avatar!}
                  alt={item.user}
                  width={40}
                  height={40}
                  className="w-10 h-10 rounded-full object-cover"
               />
                {/* Game Image */}
                <Image
                src={item.img}
                alt={item.name}
                width={50}
               height={50}
               className="rounded-lg object-cover"
               />

                <div className="flex flex-col">
                 <span className="text-sm font-semibold">
                  {item.user} • {item.time}
                 </span>
                 <span className="text-xs text-gray-400">
                  Played {item.name}
                  </span>
               </div>
                {/* Result */}
               {item.result && (
               <span
               className={`ml-auto text-xs px-2 py-1 rounded font-semibold ${
               item.result === "Won" ? "bg-green-600 text-white" : "bg-red-600 text-white"
               }`}
               >
               {item.result}
              </span>
               )}
                <span className="ml-auto text-xs bg-[#4F46E5] px-2 py-1 rounded">
                  Game Night
                </span>
              </div>
            ))}
          </div>
        </div> 
         {/* Collapsible analytic panel */}
         <CollapsiblePanel title="View your analytics 📊">

        {/* STATS */}
         <div className="bg-[#1E293B]/70 p-5 rounded-2xl text-center shadow-lg">
          <h2 className="mb-4">Your Stats</h2>

          <div className="flex justify-around mb-6">
         <div>
        <p className="text-gray-400 text-sm">Total Plays</p>
        <p className="text-2xl font-bold text-indigo-400">58</p>
        <p className="text-xs text-green-400">+11 this month</p>
          </div>

         <div>
         <p className="text-gray-400 text-sm">Win Rate</p>
         <p className="text-2xl font-bold text-indigo-400">71%</p>
         <p className="text-xs text-green-400">+6% improvement</p>
         </div>

         <div>
         <p className="text-gray-400 text-sm">Owned</p>
         <p className="text-2xl font-bold text-indigo-400">24</p>
         <p className="text-xs text-green-400">+2 new</p>
         </div>
       </div>
       </div>

      {/* CHARTS */}
       <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">

       {/* WIN RATE */}
       <div 
          onClick={() => setOpenChart("winrate")}
          className="bg-slate-800 p-4 rounded-xl h-[300px] flex flex-col cursor-pointer hover:scale-[1.02] transition"
       >
        <h2 className="mb-2 text-center">Win Rate</h2>

       <div className="flex-1 flex items-center justify-center">
        <WinRateChart className="w-full h-full" />
        </div>
       </div>

       {/* DONUT */}
       <div
         onClick={() => setOpenChart("donut")}
         className="bg-slate-800 p-4 rounded-xl h-[300px] flex flex-col items-center justify-center cursor-pointer hover:scale-[1.02] transition"
        >
        <h2 className="mb-3">Game Types</h2>

        <div
        className="w-40 h-40 rounded-full relative"
        style={{
          background:
            "conic-gradient(#4F46E5 40%, #10B981 25%, #FFBF00 20%, #EF4444 15%)",
        }}
        >
        <div className="absolute inset-6 bg-[#0F172A] rounded-full" />
        </div>

        <p className="text-gray-400 text-sm mt-2 text-center">
        Strategy • Party • Co-op • Family
        </p>
        </div>

       </div>

       </CollapsiblePanel>

        {/* BOTTOM ROW */}
        <div className="grid grid-cols-2 gap-6 mt-6">
          {/* MEMBERS */}
          <div className="bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg transition duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-indigo-500/10">
            <h2 className="mb-3">Members</h2>

            {["Brandon", "Jennifer", "Sydney", "Supriya"].map((m) => (
              <div
                key={m}
                className="flex justify-between bg-[#0F172A] p-2 rounded-lg mb-2"
              >
                <span>{m}</span>
                <span className="text-[#FFBF00] text-xs">Tag</span>
              </div>
            ))}
          </div>

        </div>
      </div>
      {openChart === "winrate" && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
    
          <div className="bg-[#1E293B] p-6 rounded-2xl w-[600px] h-[450px] relative shadow-xl">

          {/* CLOSE BUTTON */}
          <button
          onClick={() => setOpenChart(null)}
          className="absolute top-3 right-3 bg-gray-700 px-3 py-1 rounded-lg hover:bg-gray-600 transition"
        >
          ✕
         </button>

         {/* TITLE */}
          <h2 className="text-center mb-4 text-lg font-semibold">
            Win Rate Details
          </h2>

         {/* BIG CHART */}
          <div className="w-full h-[350px]">
          <WinRateChart className="w-full h-full" />
          </div>

          </div>
       </div>
      )}
      {openChart === "donut" && (
      <div
        onClick={() => setOpenChart(null)}
        className="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
       >
       <div
         onClick={(e) => e.stopPropagation()}
        className="bg-[#1E293B] p-6 rounded-2xl w-[600px] h-[450px] relative shadow-xl"
       >
       {/* CLOSE BUTTON */}
        <button
        onClick={() => setOpenChart(null)}
        className="absolute top-3 right-3 bg-gray-700 px-3 py-1 rounded-lg hover:bg-gray-600 transition"
        >
        ✕
        </button>

        {/* TITLE */}
       <h2 className="text-center mb-4 text-lg font-semibold">
         Game Types Details
        </h2>

        {/* BIG DONUT */}
        <div className="w-full h-[350px] flex items-center justify-center">
         <div
          className="w-64 h-64 rounded-full relative"
          style={{
            background:
              "conic-gradient(#4F46E5 40%, #10B981 25%, #FFBF00 20%, #EF4444 15%)",
          }}
        >
          <div className="absolute inset-12 bg-[#0F172A] rounded-full" />
        </div>
      </div>

       <p className="text-gray-400 text-sm mt-2 text-center">
        Strategy • Party • Co-op • Family
        </p>
       </div>
       </div>
       )}
      </div>
  );
}