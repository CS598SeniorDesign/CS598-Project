"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"

const AVATARS = [
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
      // TEMP: store avatar (maybe in context or localStorage)
      localStorage.setItem("userAvatar", selectedAvatar)
      router.push("/dashboardPpt") // final step
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white px-4">
      <div className="w-full max-w-lg bg-gray-900/90 backdrop-blur-md p-10 rounded-2xl shadow-2xl">
        <h1 className="text-4xl font-bold text-center mb-8">Pick Your Avatar</h1>
        <div className="grid grid-cols-3 gap-6 justify-items-center mb-8">
          {AVATARS.map((avt) => (
            <img
              key={avt}
              src={avt}
              alt="avatar"
              className={`w-28 h-28 rounded-full cursor-pointer border-4 transition-all duration-200 hover:scale-110 ${
                selectedAvatar === avt ? "border-indigo-500 scale-110 shadow-lg" : "border-gray-700 hover:border-gray-500"
              }`}
              onClick={() => setSelectedAvatar(avt)}
            />
          ))}
        </div>

        <button
          onClick={handleConfirm}
          disabled={!selectedAvatar}
          className="w-full py-3 rounded-xl font-semibold text-lg bg-primary
          hover:bg-indigo-500 
          hover:scale-[1.02]
          active:scale-95
          transition-all duration-200
          disabled:opacity-40 disabled:cursor-not-allowed "
        >
          Confirm → Dashboard
        </button>
      </div>
    </div>
  )
}