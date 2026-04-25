import Image from "next/image";

export default function UpcomingEvents() {
  const events = [
    {
      title: "Terraforming Mars Tournament",
      date: "May 24 · 7:00 PM",
      group: "The A-Team",
      image: "/images/terraforming.webp",
    },
    {
      title: "Co-op Night: Pandemic + Spirit Island",
      date: "May 26 · 6:30 PM",
      group: "Main Disaster Women",
      image: "/images/spiritIsland.webp",
    },
  ];

  return (
    <section className="border-t border-gray-600 pt-6">
      <h2 className="text-3xl font-bold mb-5 tracking-wide">
        UPCOMING EVENTS 🎮
      </h2>

      <div className="space-y-5">
        {events.map((event) => (
          <div
            key={event.title}
            className="flex gap-5 rounded-2xl border border-gray-600 bg-zinc-900 p-5"
          >
            <div className="relative w-24 h-32 rounded-xl overflow-hidden border border-gray-500 flex-shrink-0">
              <Image
                src={event.image}
                alt={event.title}
                fill
                className="object-cover"
              />
            </div>

            <div className="flex flex-col justify-center">
              <h3 className="text-2xl font-semibold mb-2">
                {event.title}
              </h3>

              <p className="text-lg text-gray-300">{event.date}</p>

              <p className="text-lg text-gray-400 mt-2">
                🎲 Hosted by{" "}
                <span className="px-3 py-1 ml-1 text-sm rounded-full bg-gray-800 border border-gray-600">
                  {event.group}
                </span>
              </p>

              <p className="text-sm text-orange-400 font-semibold mt-2">
                ⏳ Community event
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

            