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
    <section className="flex min-h-screen flex-col items-center justify-center bg-background px-6 text-center text-foreground">
      <h1 className="mb-6 bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 bg-clip-text text-5xl font-extrabold tracking-tight text-transparent sm:text-7xl md:text-8xl [html[data-theme=light]_&]:from-purple-600 [html[data-theme=light]_&]:via-pink-600 [html[data-theme=light]_&]:to-red-600">
        Game just got competitive!?
      </h1>

      <p className="mb-10 max-w-2xl text-lg leading-relaxed text-muted md:text-xl">
        QuestLog keeps the score. You bring the chaos.
      </p>

      <div className="flex flex-wrap items-center justify-center gap-4">
        {isLoading ? (
          <span
            aria-live="polite"
            className="rounded-lg bg-primary px-6 py-3 font-medium text-white opacity-60"
          >
            Loading...
          </span>
        ) : (
          <Link
            href={isAuthenticated ? "/dashboardPpt" : "/signup"}
            className="rounded-lg bg-primary px-6 py-3 font-medium text-white transition hover:opacity-90"
          >
            {isAuthenticated ? "Go to Dashboard" : "Get Started"}
          </Link>
        )}

        <Link
          href="/about"
          className="rounded-lg border border-border bg-surface px-6 py-3 font-medium text-foreground shadow-sm transition hover:border-indigo-500 hover:bg-surface-hover hover:text-link"
        >
          Learn More
        </Link>
      </div>
    </section>
  );
}
