import WinRateChart from "@/components/stats/WinRateChart";
export default function Dashboard() {
  return (
    <div className="flex min-h-screen bg-[#0F172A] text-[#F8FAFC]">

      {/* Sidebar */}
      <aside className="w-64 bg-[#1E293B] p-6 space-y-6">
        <h2 className="text-xl font-bold">Meeples</h2>

        <nav className="space-y-4">
          <div className="hover:text-[#4F46E5] cursor-pointer">Dashboard</div>
          <div className="hover:text-[#4F46E5] cursor-pointer">Library</div>
          <div className="hover:text-[#4F46E5] cursor-pointer">Groups</div>
          <div className="hover:text-[#4F46E5] cursor-pointer">Wishlist</div>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-10 space-y-10">

        {/* Header */}
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <button className="px-6 py-2 bg-[#4F46E5] rounded-lg hover:opacity-80">
            + Add Game
          </button>
        </div>

        {/* Stats Section */}
        <div className="grid grid-cols-3 gap-6">

          <div className="bg-[#1E293B] p-6 rounded-xl">
            <p className="text-gray-400">Total Games</p>
            <h3 className="text-2xl font-bold mt-2">24</h3>
          </div>

          <div className="bg-[#1E293B] p-6 rounded-xl">
            <p className="text-gray-400">Total Play Time</p>
            <h3 className="text-2xl font-bold mt-2">132 hrs</h3>
          </div>

          <div className="bg-[#1E293B] p-6 rounded-xl">
            <p className="text-gray-400">Win Rate</p>
            <h3 className="text-2xl font-bold mt-2 text-[#10B981]">64%</h3>
          </div>

        </div>

        {/* Game Cards Grid */}
        <div>
          <h2 className="text-2xl font-semibold mb-6">Recently Played</h2>

          <div className="grid grid-cols-3 gap-6">

            <div className="bg-[#1E293B] p-6 rounded-xl hover:scale-105 transition">
              <h3 className="text-lg font-semibold">Catan</h3>
              <p className="text-sm text-gray-400">Players: 3–4</p>
              <p className="mt-3">Win Rate: 65%</p>
            </div>

            <div className="bg-[#1E293B] p-6 rounded-xl hover:scale-105 transition">
              <h3 className="text-lg font-semibold">Wingspan</h3>
              <p className="text-sm text-gray-400">Players: 1–5</p>
              <p className="mt-3">Win Rate: 72%</p>
            </div>

            <div className="bg-[#1E293B] p-6 rounded-xl hover:scale-105 transition">
              <h3 className="text-lg font-semibold">Terraforming Mars</h3>
              <p className="text-sm text-gray-400">Players: 1–5</p>
              <p className="mt-3">Win Rate: 58%</p>
            </div>

          </div>
        </div>

      </main>
    </div>
  );
} 