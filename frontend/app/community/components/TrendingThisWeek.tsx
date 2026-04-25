import Image from "next/image";

export default function TrendingThisWeek() {
  const trending = [
    {
      name: "Root",
      image: "/images/root.webp",
      count: 24,
    },
    {
      name: "Wingspan",
      image: "/images/wingspan.webp",
      count: 18,
    },
    {
      name: "Betrayal at House on the Hill",
      image: "/images/betrayal.webp",
      count: 16,
    },
    {
      name: "Terraforming Mars",
      image: "/images/terraforming.webp",
      count: 30,
    },
  ];

  return (
    <section className="border-t border-gray-600 pt-6">
      <h2 className="text-3xl font-bold mb-5 tracking-wide">
        TRENDING THIS WEEK 🔥
      </h2>

      <div className="space-y-5">
        {trending.map((game, index) => (
          <div
            key={game.name}
            className="flex items-center gap-5 rounded-2xl border border-gray-700 bg-zinc-900 p-4 transition hover:scale-[1.02] hover:border-gray-400"
          >
            
            <div
              className={`w-10 h-10 rounded-full border flex items-center justify-center text-white text-lg font-bold flex-shrink-0
              ${
                index === 0
                  ? "bg-yellow-500/20 border-yellow-400"
                  : index === 1
                  ? "bg-gray-400/20 border-gray-300"
                  : index === 2
                  ? "bg-orange-500/20 border-orange-400"
                  : "bg-zinc-800 border-gray-600"
              }`}
            >
              {index + 1}
            </div>


            <div className="relative w-20 h-28 rounded-lg overflow-hidden border border-gray-600 flex-shrink-0">
              <Image
                src={game.image}
                alt={game.name}
                fill
                className="object-cover"
              />
            </div>

            <div>
              <p className="text-2xl font-semibold">{game.name}</p>
              <p className="text-lg text-gray-400 flex items-center gap-2">
                <span className="text-red-400 animate-pulse">●</span>
                 Trending in {game.count} groups this week
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}