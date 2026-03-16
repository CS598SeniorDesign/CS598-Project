"use client"

import Link from "next/link"

export default function Navbar() {
  return (
    <nav className="w-full flex justify-between items-center px-10 mt-32">

      {/* Logo */}
      <Link
        href="/"
        className="text-4xl font-bold text-white tracking-wide"
      >
        QuestLog
      </Link>

      {/* Right side links */}
      <div className="flex items-center text-xl">

        <Link
          href="/login"
          className="hover:text-gray-400 transition"
        >
          Login
        </Link>

        <Link
          href="/signup"
          className="ml-8 bg-indigo-600 px-5 py-2 rounded-lg hover:bg-indigo-500 transition"
        >
          Sign Up
        </Link>

      </div>

    </nav>
  )
}