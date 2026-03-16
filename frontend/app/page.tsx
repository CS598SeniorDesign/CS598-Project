export default function HomePage() {
  return (
    <section className="min-h-screen flex flex-col items-center justify-center bg-background text-white px-6">
      
      <h1 className="text-7xl md:text-8xl font-extrabold tracking-light mb-6 bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 bg-clip-text text-transparent">
        Game just got competitive!?
      </h1>

      <p className="text-lg md:text-xl text-gray-400 mb-10 max-w-2xl leading-relaxed">
        QuestLog keeps the score. You bring the chaos.
      </p>

      <div className="flex gap-4">
        <button className="bg-primary px-6 py-3 rounded-lg">
          Get Started
        </button>

        <button className="border border-gray-700 px-6 py-3 rounded-lg">
          Learn More
        </button>
      </div>

    </section>
  )
}

<div className="bg-red-500 text-white p-10 mt-20">
  Tailwind Test
</div>