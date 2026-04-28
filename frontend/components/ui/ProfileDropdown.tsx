"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function ProfileDropdown() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  const handleNavigate = (path: string) => {
    setOpen(false);
    router.push(path);
  };

  return (
    <div className="relative">
      {/* Profile Circle Button */}
      <button
        onClick={() => setOpen(!open)}
        className="w-10 h-10 rounded-full bg-gray-700 text-white flex items-center justify-center"
      >
        U
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 mt-2 w-48 bg-white shadow-lg rounded-xl overflow-hidden z-50">
          <button
            onClick={() => handleNavigate("/profile")}
            className="w-full text-left px-4 py-2 hover:bg-gray-100"
          >
            View Profile
          </button>

          <button
            onClick={() => handleNavigate("/settings")}
            className="w-full text-left px-4 py-2 hover:bg-gray-100"
          >
            Settings
          </button>

          <button
            onClick={() => handleNavigate("/privacy")}
            className="w-full text-left px-4 py-2 hover:bg-gray-100"
          >
            Privacy
          </button>

          <hr />

          <button className="w-full text-left px-4 py-2 hover:bg-gray-100 text-red-500">
            Logout
          </button>
        </div>
      )}
    </div>
  );
}