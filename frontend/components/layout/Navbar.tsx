"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type SessionResponse = { meta?: { is_authenticated?: boolean } };

function getCookie(name: string): string | null {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.substring(name.length + 1)) : null;
}

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function checkSession() {
      setIsLoading(true);
      try {
        const response = await fetch("/_allauth/browser/v1/auth/session", {
          credentials: "same-origin",
          cache: "no-store",
        });
        if (!active) return;
        if (!response.ok) {
          setIsAuthenticated(false);
          return;
        }
        const result: SessionResponse = await response.json();
        if (active) setIsAuthenticated(result.meta?.is_authenticated === true);
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
  }, [pathname]);

  async function handleLogout() {
    if (isLoggingOut) return;
    setIsLoggingOut(true);
    setError("");
    try {
      const csrfToken = getCookie("csrf_token");
      if (!csrfToken)
        throw new Error("Missing security token. Refresh and try again.");
      const response = await fetch("/_allauth/browser/v1/auth/session", {
        method: "DELETE",
        credentials: "same-origin",
        headers: { "X-CSRFToken": csrfToken },
      });
      if (!response.ok && response.status !== 401)
        throw new Error("Unable to log out. Please try again.");
      setIsAuthenticated(false);
      router.replace("/login");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to log out.");
    } finally {
      setIsLoggingOut(false);
    }
  }

  // The dashboard provides its own navigation, including the account dropdown.
  if (pathname === "/dashboardPpt" || pathname.startsWith("/dashboardPpt/"))
    return null;

  return (
    <header className="w-full bg-[#111827] text-[#F8FAFC] shadow-lg">
      <nav
        aria-label="Main navigation"
        className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-5 py-4 lg:px-8"
      >
        <Link
          href="/"
          className="text-2xl font-extrabold tracking-tight transition hover:text-indigo-300"
        >
          QuestLog
        </Link>
        {!isLoading && (
          <div className="flex items-center gap-4 text-sm">
            {isAuthenticated ? (
              <button
                type="button"
                onClick={() => void handleLogout()}
                disabled={isLoggingOut}
                className="rounded-lg bg-indigo-600 px-4 py-2 font-medium transition hover:bg-indigo-500 disabled:opacity-50"
              >
                {isLoggingOut ? "Logging Out..." : "Log Out"}
              </button>
            ) : (
              <>
                <Link href="/login" className="hover:text-indigo-300">
                  Login
                </Link>
                <Link
                  href="/signup"
                  className="rounded-lg bg-indigo-600 px-4 py-2 font-medium transition hover:bg-indigo-500"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        )}
      </nav>
      {error && (
        <p role="alert" className="px-8 pb-3 text-right text-sm text-red-400">
          {error}
        </p>
      )}
    </header>
  );
}
