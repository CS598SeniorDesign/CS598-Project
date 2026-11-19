"use client";

import { useState } from "react";

export default function NotificationIcon() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        aria-label="Event notifications"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-red-700 text-3xl font-bold text-white transition hover:bg-red-600"
      >
        !
      </button>

      {open && (
        <div className="absolute left-1/2 top-14 z-50 w-72 -translate-x-1/2 rounded-xl border border-border bg-surface px-4 py-3 text-center text-lg text-foreground shadow-xl">
          Event Reminder ! Upcoming event on Feb13
        </div>
      )}
    </div>
  );
}
