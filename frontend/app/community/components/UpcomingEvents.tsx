export default function UpcomingEvents() {
  return (
    <section className="border-t border-gray-600 pt-6">
      <h2 className="mb-5 text-3xl font-bold tracking-wide">
        UPCOMING EVENTS 🎮
      </h2>

      <div className="rounded-2xl border border-gray-700 bg-zinc-900 p-6">
        <div className="flex flex-col items-center gap-4 py-6 text-center">
          {/* Event icon */}
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-indigo-500/15">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-indigo-400"
              aria-hidden="true"
            >
              <rect x="3" y="5" width="18" height="16" rx="2" />
              <path d="M16 3v4M8 3v4M3 10h18" />
              <path d="m9 16 2 2 4-4" />
            </svg>
          </div>

          <div>
            <h3 className="text-xl font-semibold">No upcoming events yet</h3>

            <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-gray-400">
              Game nights, tournaments, and community events will appear here
              when event scheduling becomes available in QuestLog.
            </p>
          </div>

          <div className="mt-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-sm font-medium text-indigo-300">
            Event scheduling coming soon
          </div>
        </div>
      </div>
    </section>
  );
}
