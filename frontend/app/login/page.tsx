"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"
import "../../style/auth.css" // same CSS as signup

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()

    // TODO: Replace with real authentication logic
    if (email && password) {
      router.push("/avatar-selection") // redirect to Avatar Picker
    } else {
      alert("Please enter email and password")
    }
  }

  return (
    <div className="signup-page-container">
      <div className="signup-card">
        <h1 className="signup-title">Login</h1>

        <form className="signup-form" onSubmit={handleSubmit} autoComplete="off">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="signup-input"
            autoComplete="off"
            required
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="signup-input"
            autoComplete="new-password"
            required
          />

          <button type="submit" className="signup-button login">
            Sign In
          </button>
        </form>

        <p className="signup-login-text">
          Don't have an account?{" "}
          <a href="/signup" className="signup-login-link">
            Sign Up
          </a>
        </p>
      </div>
    </div>
  )
}