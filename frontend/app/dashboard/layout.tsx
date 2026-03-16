import Sidebar from "@/components/layout/Sidebar";
import GameCard from "@/components/games/GameCard"
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-[#0F172A] text-gray-100">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 p-8">
        {/* Dashboard Grid */}
        <div className="grid grid-cols-3 gap-10">
          
          {/* Recent Games Section */}
          <section className="col-span-2">
            <h2 className="text-2xl font-bold mb-4">Recent Group Games</h2>
            <div className="grid grid-cols-3 gap-6">
              {/** Example usage of GameCard */}
              <GameCard 
                title="Catan"
                playerCount="3-4"
                complexity="Medium"
                winRate="50%"
                tags={['Strategy', 'Family']}
              />
              <GameCard 
                title="Gloomhaven"
                playerCount="1-4"
                complexity="High"
                winRate="70%"
                tags={['Adventure', 'Campaign']}
              />
              <GameCard 
                title="Ticket to Ride"
                playerCount="2-5"
                complexity="Low"
                winRate="60%"
                tags={['Strategy', 'Family']}
              />
            </div>
          </section>

          {/* Calendar Section */}
          <section>
            <h2 className="text-2xl font-bold mb-4">Calendar</h2>
            <div className="bg-slate-800 h-64 rounded-xl flex items-center justify-center text-gray-400">
              Calendar Component Here
            </div>
          </section>

        </div>
      </main>
    </div>
  );
}