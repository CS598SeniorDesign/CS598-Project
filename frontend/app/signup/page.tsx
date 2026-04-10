'use client'

import { useRouter } from "next/navigation"
import { useState } from "react"
import "../../style/auth.css";

export default function SignupPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [mfa, setMfa] = useState(false)
  const [privacy, setPrivacy] = useState("public")

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()

    // TODO: remove temporary local storage logic after backend auth is implemented.
    console.log({ email, password, privacy })

    // redirect to MFA setup page
    router.push("/mfa-setup")
  }

  return (
    <div className="signup-page-container">
      <div className="signup-card">
        <h1 className="signup-title">Create Account</h1>

        <form onSubmit={handleSubmit} autoComplete="off" className="signup-form">
          <input
            type="email"
            placeholder="Email"
            autoComplete="off"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="signup-input"
            required
          />

          <input
            type="password"
            placeholder="Password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="signup-input"
            required
          />

          <select
            value={privacy}
            onChange={(e) => setPrivacy(e.target.value)}
            className="signup-input"
          >
            <option value="public">Public</option>
            <option value="friends">Friends Only</option>
            <option value="private">Private</option>
          </select>

          <button type="submit" className="signup-button">
            Sign Up
          </button>
        </form>

        <p className="signup-login-text">
          Already have an account?{" "}
          <a href="/login" className="signup-login-link">Login</a>
        </p>
      </div>
    </div>
  )
}