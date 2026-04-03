"use client"

import { useRouter } from "next/navigation"
import "../../style/auth.css" // use same CSS

export default function MFASetup() {
  const router = useRouter()

  const handleEnable = () => {
    // TODO: implement the MFA setup
    router.push("/login")
  }

  const handleSkip = () => {
    router.push("/login")
  }

  return (
    <div className="signup-page-container">
      <div className="signup-card mfa-card">
        <h1 className="signup-title">Secure Your Account</h1>

        <p className="mfa-text">
          You can enable Multi-Factor Authentication for additional security.
        </p>

        <div className="mfa-buttons">
          <button className="signup-button enable-mfa" onClick={handleEnable}>
            Enable MFA
          </button>

          <button className="signup-button skip-mfa" onClick={handleSkip}>
            Skip
          </button>
        </div>
      </div>
    </div>
  )
}