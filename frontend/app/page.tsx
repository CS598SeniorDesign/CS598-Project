"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type SessionResponse = {
  meta?: {
    is_authenticated?: boolean;
  };
};

export default function HomePage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function checkSession() {
      try {
        const response = await fetch("/_allauth/browser/v1/auth/session", {
          credentials: "same-origin",
          cache: "no-store",
        });

        if (!response.ok) return;

        const result: SessionResponse = await response.json();

        if (active) {
          setIsAuthenticated(result.meta?.is_authenticated === true);
        }
      } catch {
        if (active) setIsAuthenticated(false);
      } finally {
        if (active) setIsLoading(false);
      }
    }

    void checkSession();

    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="min-h-screen flex flex-col items-center justify-center bg-background text-white px-6">
      <h1 className="text-7xl md:text-8xl font-extrabold tracking-light mb-6 bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 bg-clip-text text-transparent">
        Game just got competitive!?
      </h1>

      <p className="text-lg md:text-xl text-gray-400 mb-10 max-w-2xl leading-relaxed">
        QuestLog keeps the score. You bring the chaos.
      </p>

      <div className="flex flex-wrap gap-4">
        {isLoading ? (
          <span
            aria-live="polite"
            className="bg-primary px-6 py-3 rounded-lg opacity-60"
          >
            Loading...
          </span>
        ) : (
          <Link
            href={isAuthenticated ? "/dashboardPpt" : "/signup"}
            className="bg-primary px-6 py-3 rounded-lg hover:opacity-90 transition"
          >
            {isAuthenticated ? "Go to Dashboard" : "Get Started"}
          </Link>
        )}

        <Link
          href="/about"
          className="border border-gray-700 px-6 py-3 rounded-lg hover:border-purple-400 hover:text-purple-300 transition"
        >
          Learn More
        </Link>
      </div>
    </section>
  );
}
