"use client"

import { useRouter } from "next/navigation"

export default function MFASetup() {

    const router = useRouter()

    const handleEnable = () => {
        //later this would then setup MFA
        router.push("/login")
    }

    const handleSkip = () => {
        router.push("/login")
    }
  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white">

      <div className="bg-gray-900 p-8 rounded-xl text-center max-w-md">

        <h1 className="text-3xl font-bold mb-4">
          Secure Your Account
        </h1>

        <p className="text-gray-400 mb-6">
          You can enable Multi-Factor Authentication for additional security.
        </p>

        <div className="flex gap-4 justify-center">

          <button
             className="bg-indigo-600 px-6 py-2 rounded-lg hover:opacity-90 transition"
             onClick={handleEnable}
          >
            Enable MFA
          </button>

          <button 
             className="border border-gray-600 px-6 py-2 rounded-lg"
             onClick={handleSkip}   
          >
            Skip
          </button>

        </div>

      </div>

    </div>
  )
}