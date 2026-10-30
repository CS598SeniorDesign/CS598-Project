"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type SessionResponse = {
  meta?: {
    is_authenticated?: boolean;
  };
};

function getCookie(name: string): string | null {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.substring(name.length + 1)) : null;
}

export default function Navbar() {
  const router = useRouter();

  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function checkSession() {
      try {
        const response = await fetch("/_allauth/browser/v1/auth/session", {
          credentials: "same-origin",
          cache: "no-store",
        });

        if (!response.ok) {
          setIsAuthenticated(false);
          return;
        }

        const result: SessionResponse = await response.json();

        setIsAuthenticated(result.meta?.is_authenticated === true);
      } catch {
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    }

    void checkSession();
  }, []);

  async function handleLogout() {
    if (isLoggingOut) return;

    setIsLoggingOut(true);
    setError("");

    try {
      const csrfToken = getCookie("csrf_token");

      if (!csrfToken) {
        throw new Error(
          "Missing security token. Please refresh and try again.",
        );
      }

      const response = await fetch("/_allauth/browser/v1/auth/session", {
        method: "DELETE",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken,
        },
      });

      if (!response.ok) {
        throw new Error("Unable to log out. Please try again.");
      }

      setIsAuthenticated(false);
      router.replace("/login");
      router.refresh();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while logging out.",
      );
    } finally {
      setIsLoggingOut(false);
    }
  }

  return (
    <nav className="w-full flex flex-col px-10 mt-32">
      <div className="w-full flex justify-between items-center">
        {/* Logo */}
        <Link href="/" className="text-4xl font-bold text-white tracking-wide">
          QuestLog
        </Link>

        {/* Navigation Links */}
        <div className="flex items-center gap-6 text-xl">
          <Link href="/login" className="hover:text-gray-400 transition">
            Login
          </Link>

          <Link href="/signup" className="hover:text-gray-400 transition">
            Sign Up
          </Link>

          {!isLoading && isAuthenticated && (
            <button
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="bg-indigo-600 px-5 py-2 rounded-lg hover:bg-indigo-500 transition disabled:opacity-50"
            >
              {isLoggingOut ? "Logging Out..." : "Log Out"}
            </button>
          )}
        </div>
      </div>

      {error && (
        <p role="alert" className="text-red-400 text-sm mt-3 text-right">
          {error}
        </p>
      )}
    </nav>
  );
}
