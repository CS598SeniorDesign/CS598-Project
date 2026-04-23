import GameGroups from "./components/GameGroups";
import FriendsList from "./components/FriendsList";
import UpdatesFeed from "./components/UpdatesFeed";
import TrendingThisWeek from "./components/TrendingThisWeek";
import UpcomingEvents from "./components/UpcomingEvents";

export default function CommunityPage() {
  return (
    <main className="px-8 py-10 max-w-[1600px] mx-auto">
      <h1 className="text-center text-6xl font-bold mb-10 tracking-widest">
        THE WEEPLES
      </h1>

      <div className="grid grid-cols-2 gap-4 border-t border-gray-600 pt-6">
        <div className="border-r border-gray-600 pr-8 space-y-10">
          <GameGroups />
          <FriendsList />
          <TrendingThisWeek />
        </div>

        <div className="pl-8 space-y-10">
          <UpdatesFeed />
          <UpcomingEvents />
        </div>
      </div>
    </main>
  );
}