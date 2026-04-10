"use client";

import Image from "next/image";
import React, { useState, useEffect } from "react";
import Link from "next/link";
import WinRateChart from "@/components/stats/WinRateChart";
import CollapsiblePanel from "@/components/ui/CollapsiblePanel";
import "../../style/auth.css"; // our plain CSS

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

export default function Page() {
  type Game = { name: string; img: string };
  type Play = { name: string; img: string; result: "Won" | "Lost"; players: number; time: string; date: string };
  type CommunityItem = { name: string; img: string | StaticImageData; user: string; time: string; result: "Won" | "Lost"; avatar?: string | StaticImageData };

  const games: Game[] = [
    { name: "Botany", img: "/images/botany.webp" },
    { name: "Stardew Valley", img: "/images/stardew.webp" },
    { name: "Pandemic", img: "/images/pandemic.webp" },
    { name: "Root", img: "/images/root.webp" },
    { name: "Catan", img: "/images/catan.webp" },
  ];

  const recentPlays: Play[] = [
    { name: "Terraforming Mars", img: "/images/terraforming.webp", result: "Won", players: 2, time: "90 min", date: "Feb 22" },
    { name: "Catan", img: "/images/catan.webp", result: "Lost", players: 4, time: "60 min", date: "March 11" },
    { name: "Azul", img: "/images/azul.webp", result: "Won", players: 3, time: "30 min", date: "January 21" },
  ];

  const community: CommunityItem[] = [
    { user: "Brandon", time: "2hrs ago", result: "Won", avatar: brandonAvatar, name: "Terraforming Mars", img: terraformImg },
    { user: "Sydney", time: "5hrs ago", result: "Lost", avatar: sydneyAvatar, name: "Catan", img: catanImg },
    { user: "Jennifer", time: "1d ago", result: "Won", avatar: jenniferAvatar, name: "Everdell", img: everdellImg },
    { user: "Supriya", time: "2d ago", result: "Lost", avatar: supriyaAvatar, name: "Botany", img: botanyImg },
  ];

  const days: string[] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const [openChart, setOpenChart] = useState<null | "winrate" | "donut">(null);

  // state for avatar to fix hydration
  const [userAvatar, setUserAvatar] = useState<string | null>(null);
  useEffect(() => {
    const avatar = localStorage.getItem("userAvatar");
    if (avatar) setUserAvatar(avatar);
  }, []);

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
                <Link key={i} href={`/games/${game.name}`}>
                  <div className="card-inner cursor-pointer">
                    <img src={game.img} alt={game.name} />
                    <p>{game.name}</p>
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
                <img src={play.img} alt={play.name} />
                <div>
                  <p>{play.name}</p>
                  <p>{play.date} | {play.players} Players | {play.time}</p>
                </div>
                <span className={play.result === "Won" ? "play-result-won" : "play-result-lost"}>{play.result}</span>
              </div>
            ))}
          </div>

          {/* COMMUNITY */}
          <div className="card card-hover">
            <h2>Weeple Community Feed</h2>
            {community.map((item, i) => (
              <div key={i} className="card-inner community-item">
                <Image src={item.avatar!} alt={item.user} width={40} height={40} />
                <Image src={item.img} alt={item.name} width={50} height={50} />
                <div>
                  <span>{item.user} • {item.time}</span>
                  <span>Played {item.name}</span>
                </div>
                {item.result && (
                  <span className={item.result === "Won" ? "result-badge-won" : "result-badge-lost"}>
                    {item.result}
                  </span>
                )}
                <span className="game-night-badge">Game Night</span>
              </div>
            ))}
          </div>
        </div>

        {/* COLLAPSIBLE ANALYTICS */}
        <CollapsiblePanel title="View your analytics 📊">
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