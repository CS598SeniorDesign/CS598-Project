"use client";

import Image from "next/image";
import React, { useState, useEffect } from "react";
import Link from "next/link";
import WinRateChart from "@/components/stats/WinRateChart";

// avatars
import brandonAvatar from "@/public/avatars/brandon.webp";
import sydneyAvatar from "@/public/avatars/sydney.webp";
import jenniferAvatar from "@/public/avatars/jennifer.webp";
import supriyaAvatar from "@/public/avatars/supriya.webp";
import { StaticImageData } from "next/image";

// game images
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
  //TODO: extend to include score or draw in future
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

const days: string[] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function Page() {
  const [openChart, setOpenChart] = useState<null | "winrate" | "donut">(null);
  // state for avatar to fix hydration
  const [userAvatar, setUserAvatar] = useState<string | null>(null);
  useEffect(() => {
    const avatar = localStorage.getItem("userAvatar");
    if (avatar) setUserAvatar(avatar);
  }, []);

  const scrollToAnalytics = () => {
    document.getElementById("analytics")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };
  const games: Game[] = [
    { gameName: "Botany", gameImg: "/images/botany.webp" },
    { gameName: "Stardew Valley", gameImg: "/images/stardew.webp" },
    { gameName: "Pandemic", gameImg: "/images/pandemic.webp" },
    { gameName: "Root", gameImg: "/images/root.webp" },
    { gameName: "Catan", gameImg: "/images/catan.webp" },
   ];

  const recentPlays: Play[] = [
    { gameName: "Terraforming Mars", gameImg: "/images/terraforming.webp", gameResult:"Won", playerCount: 2, playDuration: "90 min", playDate: "Feb 22" },
    { gameName: "Catan", gameImg: "/images/catan.webp", gameResult: "Lost", playerCount: 4, playDuration: "60 min", playDate: "March 11" },
    { gameName: "Azul", gameImg: "/images/azul.webp", gameResult: "Won", playerCount: 3, playDuration: "30 min", playDate: "January 21" },
   ];

  const community: CommunityItem[] = [
    { user: "Brandon", timeAgo: "2hrs ago", gameResult: "Won", avatar: brandonAvatar, gameName: "Terraforming Mars", gameImg: terraformImg },
    { user: "Sydney", timeAgo: "5hrs ago", gameResult: "Lost", avatar: sydneyAvatar, gameName: "Catan", gameImg: catanImg },
    { user: "Jennifer", timeAgo: "1d ago", gameResult: "Won", avatar: jenniferAvatar, gameName: "Everdell", gameImg: everdellImg },
    { user: "Supriya", timeAgo: "2d ago", gameResult: "Lost", avatar: supriyaAvatar, gameName: "Botany", gameImg: botanyImg },
   ];


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
        <Link href="/community">
          <p className="hover:text-white cursor-pointer transition">
            Weeple
          </p>
        </Link>
        
          <Link href="/analytics">
            <p className="hover:text-white cursor-pointer transition">
              Your Analytics
            </p>
          </Link>
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
        <h1 className="text-4xl font-extrabold tracking-tight text-white">Welcome to QuestLog</h1>
        <p className="text-gray-400 mb-6">Your shared activity hub</p>

        {/* TOP ROW */}
        <div className="grid grid-cols-3 gap-6">
          {/* RECENT GROUP GAMES */}
          <div className="col-span-2 bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg transition duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-indigo-500/10">
            <h2 className="mb-4 text-gray-300">Recently Played</h2>

            <div className="flex gap-5">
              {games.map((game, i) => (
               <Link key={i} href={`/games/${game.gameName}`}>
                <div className="w-44 cursor-pointer">
                 <Image
                  src={game.gameImg} alt={game.gameName} width={200} height={160}
                  className="rounded-xl mb-2 h-40 w-full object-cover transition duration-300 hover:scale-105 hover:shadow-[0_0_20px_rgba(79,70,229,0.4)]"
                 />
                   <p className="text-sm font-semibold">{game.gameName}</p>
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
                <Image
                  src={play.gameImg} alt={play.gameName} width={48} height={48}
                  className="w-12 h-12 rounded-lg object-cover"
                />

                <div className="flex-1">
                  <p className="text-sm font-semibold">{play.gameName}</p>
                  <p className="text-xs text-gray-400">
                    {play.playDate} | {play.playerCount} Players | {play.playDuration}
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
                {/* Result */}
               {item.gameResult && (
               <span
               className={`ml-auto text-xs px-2 py-1 rounded font-semibold ${
               item.gameResult === "Won" ? "bg-green-600 text-white" : "bg-red-600 text-white"
               }`}
               >
               {item.gameResult}
              </span>
               )}
                <span className="ml-auto text-xs bg-[#4F46E5] px-2 py-1 rounded">
                  Game Night
                </span>
              </div>
            ))}
          </div>
        </div> 

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
    </div>
  );
}