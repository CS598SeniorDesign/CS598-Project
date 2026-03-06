"use client"

import Link from "next/link"

export default function Navbar() {
  return (
    <nav className="w-full bg-black border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-6 py-8 flex justify-between items-center">

        {/* Logo */}
        <Link href="/" className="text-4xl font-bold text-white tracking-wide">
          QuestLog
        </Link>

        {/* Right Side */}
        <div className="flex items-center text-xl font-medium gap-6">
          <Link
            href="/login"
            className="hover:text-gray-400 transition duration-200 px-4"
          >
            Login
          </Link>

          <Link
            href="/signup"
            className="bg-primary px-4 py-2 rounded-lg hover:text-gray-400 transition duration-200"
          >
            Sign Up
          </Link>
        </div>

      </div>
    </nav>
  )
}