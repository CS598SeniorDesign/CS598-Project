"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"

export default function SignupPage() {
  const router = useRouter()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [mfa, setMfa] = useState(false)
  const [privacy, setPrivacy] = useState("public")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // TEMPORARY: just redirect to MFA setup page
    router.push("/mfa-setup")
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white">
      <div className="w-full max-w-md bg-gray-900 p-8 rounded-xl">
        <h1 className="text-3xl font-bold mb-6">Create Account</h1>

        <form onSubmit={handleSubmit} autoComplete="off" className="flex flex-col gap-4">

          <input
            type="email"
            placeholder="Email"
            autoComplete="off"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="p-3 rounded bg-gray-800 border border-gray-700"
            required
          />

          <input
            type="password"
            placeholder="Password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="p-3 rounded bg-gray-800 border border-gray-700"
            required
          />

          <select
            value={privacy}
            onChange={(e) => setPrivacy(e.target.value)}
            className="p-3 rounded bg-gray-800 border border-gray-700"
          >
            <option value="public">Public</option>
            <option value="friends">Friends Only</option>
            <option value="private">Private</option>
          </select>

          <button
            type="submit"
            className="bg-primary py-2 rounded-lg hover:opacity-90"
          >
            Sign Up
          </button>

        </form>

        {/* Link to Login */}
        <p className="text-sm text-gray-400 mt-6 text-center">
          Already have an account?{" "}
          <a href="/login" className="text-indigo-400 hover:underline">
           Login
          </a>
        </p>
      </div>
    </div>
  )
}