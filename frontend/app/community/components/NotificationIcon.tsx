"use client";
import { useState } from "react";

export default function NotificationIcon() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="bg-red-600 w-6 h-6 rounded-full flex items-center justify-center text-white"
      >
        !
      </button>

      {open && (
        <div className="absolute top-10 right-0 bg-gray-700 text-sm p-3 rounded-lg shadow-lg w-56">
          Event Reminder! Upcoming event on [Date]
        </div>
      )}
    </div>
  );
}