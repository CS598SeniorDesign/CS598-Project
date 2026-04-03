"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import "../../style/auth.css" // use the same CSS

const avatars = [
  "/avatars/brandon.webp",
  "/avatars/sydney.webp",
  "/avatars/jennifer.webp",
  "/avatars/supriya.webp",
  "/avatars/avatar1.webp",
  "/avatars/avatar2.webp",
  "/avatars/avatar3.webp",
  "/avatars/avatar4.webp",
  "/avatars/avatar5.webp", 
]

export default function AvatarSelectionPage() {
  const router = useRouter()
  const [selectedAvatar, setSelectedAvatar] = useState<string>("")

  const handleConfirm = () => {
    if (selectedAvatar) {
      localStorage.setItem("userAvatar", selectedAvatar) //store the avatar in localStorage
      router.push("/dashboardPpt")
    }
  }

  return (
    <div className="auth-page-container">
      <div className="auth-card">
        <h1 className="auth-title">Pick Your Avatar</h1>

        <div className="avatar-grid">
          {avatars.map((avt) => (
            <img
              key={avt}
              src={avt}
              alt="avatar"
              className={`avatar-image ${
                selectedAvatar === avt ? "avatar-selected" : ""
              }`}
              onClick={() => setSelectedAvatar(avt)}
            />
          ))}
        </div>

        <button
          onClick={handleConfirm}
          disabled={!selectedAvatar}
          className="auth-button w-full"
        >
          Confirm → Dashboard
        </button>
      </div>
    </div>
  )
}