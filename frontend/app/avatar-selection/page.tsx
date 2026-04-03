"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"

const avatars = [
  "/avatars/brandon.webp",
  "/avatars/sydney.webp",
  "/avatars/jennifer.webp",
  "/avatars/supriya.webp",
  "/avatars/avatar1.webp",
  "/avatars/avatar2.webp",
  "/avatars/avatar3.webp",
  "/avatars/avatar4.webp",
  "/avatars/avatar5.webpp",
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
    <div className="min-h-screen flex items-center justify-center bg-black text-white">
      <div className="w-full max-w-md bg-gray-900 p-8 rounded-xl">
        <h1 className="text-3xl font-bold mb-6">Pick Your Avatar</h1>
        <div className="grid grid-cols-2 gap-4 mb-6">
          {avatars.map((avt) => (
            <img
              key={avt}
              src={avt}
              alt="avatar"
              className={`w-20 h-20 rounded-full cursor-pointer border-4 ${
                selectedAvatar === avt ? "border-indigo-500" : "border-gray-700"
              }`}
              onClick={() => setSelectedAvatar(avt)}
            />
          ))}
        </div>

        <button
          onClick={handleConfirm}
          disabled={!selectedAvatar}
          className="bg-primary py-2 rounded-lg hover:opacity-90 w-full disabled:opacity-50"
        >
          Confirm → Dashboard
        </button>
      </div>
    </div>
  )
}