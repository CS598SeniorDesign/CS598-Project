"use client";

import { useState } from "react";

export default function NotificationIcon() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-12 h-12 rounded-full bg-red-700 text-white text-3xl font-bold flex items-center justify-center hover:bg-red-600 transition"
      >
        !
      </button>

      {open && (
        <div className="absolute top-14 left-1/2 -translate-x-1/2 w-72 rounded-xl border border-gray-400 bg-gray-700 px-4 py-3 text-center text-lg shadow-xl z-50">
          Event Reminder ! Upcoming event on Feb13
        </div>
      )}
    </div>
  );
}