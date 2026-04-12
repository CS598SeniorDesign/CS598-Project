"use client";

import Image from "next/image";
import React, { useState, useEffect } from "react";
import Link from "next/link";
import WinRateChart from "@/components/stats/WinRateChart";
import CollapsiblePanel from "@/components/ui/CollapsiblePanel";
import "../../style/auth.css"; 


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
    <div className="dashboard-page">
      {/* NAVBAR */}
      <div className="dashboard-navbar">
        <h1>QuestLog</h1>
        <div className="nav-links">
          <p className="active">Game Library</p>
          <Link href="/games/search"><p>Recommendations for you</p></Link>
          <p>Weeple</p>
        </div>
        <div className="user-info">
          {userAvatar ? (
            <img src={userAvatar} alt="User Avatar" />
          ) : (
            <div className="default-avatar" />
          )}
          <p>MeepleTeam</p>
        </div>
      </div>

      <div className="dashboard-content">
        <h1>Welcome to QuestLog</h1>
        <p>Your shared activity hub</p>

        {/* TOP ROW */}
        <div className="dashboard-grid">
          {/* RECENT GAMES */}
          <div className="card card-hover">
            <h2>Recently Played</h2>
            <div className="recent-games">
              {games.map((game, i) => (
                <Link key={i} href={`/games/${game.gameName}`}>
                  <div className="card-inner cursor-pointer">
                    <Image src={game.gameImg} alt={game.gameName} width={90} height={90} />
                    <p>{game.gameName}</p>
                    <div className="rating">★★★★★</div>
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* CALENDAR */}
          <div className="card card-hover">
            <h2>Calendar</h2>
            <h3>FEBRUARY</h3>
            <div className="calendar-header">
              {days.map((d) => <div key={d}>{d}</div>)}
            </div>
            <div className="calendar-grid">
              {[...Array(31)].map((_, i) => (
                <div key={i} className="calendar-day">
                  {i + 1}
                  {(i === 9 || i === 22) && <div className="calendar-badge">Game</div>}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* MIDDLE ROW */}
        <div className="dashboard-grid">
          {/* RECENT PLAYS */}
          <div className="card card-hover">
            <h2>Recent Plays</h2>
            {recentPlays.map((play, i) => (
              <div key={i} className="card-inner">
                <Image src={play.gameImg} alt={play.gameName} width={60} height={60} />
                <div>
                  <p>{play.gameName}</p>
                  <p>{play.playDate} | {play.playerCount} Players | {play.playDuration}</p>
                </div>
                <span className={play.gameResult === "Won" ? "play-result-won" : "play-result-lost"}>{play.gameResult}</span>
              </div>
            ))}
          </div>

          {/* COMMUNITY */}
          <div className="card card-hover">
            <h2>Weeple Community Feed</h2>
            {community.map((item, i) => (
              <div key={i} className="card-inner community-item">
                <Image src={item.avatar!} alt={item.user} width={40} height={40} />
                <Image src={item.gameImg} alt={item.gameName} width={50} height={50} />
                <div>
                  <span>{item.user} • {item.timeAgo}</span>
                  <span>Played {item.gameName}</span>
                </div>
                {item.gameResult && (
                  <span className={item.gameResult === "Won" ? "result-badge-won" : "result-badge-lost"}>
                    {item.gameResult}
                  </span>
                )}
                <span className="game-night-badge">Game Night</span>
              </div>
            ))}
          </div>
        </div>

        {/* COLLAPSIBLE ANALYTICS */}
        <CollapsiblePanel sectionTitle="View your analytics 📊">
          <div className="card">
            <h2>Your Stats</h2>
            <div className="stats-row">
              <div>
                <p>Total Plays</p>
                <p>58</p>
                <p>+11 this month</p>
              </div>
              <div>
                <p>Win Rate</p>
                <p>71%</p>
                <p>+6% improvement</p>
              </div>
              <div>
                <p>Owned</p>
                <p>24</p>
                <p>+2 new</p>
              </div>
            </div>

            {/* CHARTS */}
            <div className="charts-row">
              <div onClick={() => setOpenChart("winrate")} className="card chart-hover chart-card">
                <h2>Win Rate</h2>
                <div className="chart-container">
                  <WinRateChart className="chart-full" />
                </div>
              </div>

              <div onClick={() => setOpenChart("donut")} className="card chart-hover chart-card">
                <h2>Game Types</h2>
                <div className="game-type-donut" style={{background: "conic-gradient(#4F46E5 40%, #10B981 25%, #FFBF00 20%, #EF4444 15%)"}}>
                  <div className="game-type-donut-inner"></div>
                </div>
                <p>Strategy • Party • Co-op • Family</p>
              </div>
            </div>
          </div>
        </CollapsiblePanel>
        <div className="member-list">
         {["Brandon", "Jennifer", "Sydney", "Supriya"].map((name, i) => (
          <div key={i} className="member-row">
            <span>{name}</span>
            <span className="member-tag">Tag</span>
          </div>
         ))}
        </div>
      </div>
    </div>
  );
}