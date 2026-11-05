import GameGroups from "./components/GameGroups";
import FriendsList from "./components/FriendsList";
import UpdatesFeed from "./components/UpdatesFeed";
import TrendingThisWeek from "./components/TrendingThisWeek";
import UpcomingEvents from "./components/UpcomingEvents";

export default function CommunityPage() {
  return (
    <main className="mx-auto w-full max-w-[1600px] px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <h1 className="mb-8 text-center text-3xl font-bold tracking-widest sm:text-4xl md:mb-10 md:text-5xl lg:text-6xl">
        THE WEEPLES
      </h1>

      <div className="grid grid-cols-1 gap-10 border-t border-gray-600 pt-6 lg:grid-cols-2 lg:gap-4">
        <div className="min-w-0 space-y-10 lg:border-r lg:border-gray-600 lg:pr-8">
          <GameGroups />
          <FriendsList />
          <TrendingThisWeek />
        </div>

        <div className="min-w-0 space-y-10 border-t border-gray-600 pt-8 lg:border-t-0 lg:pt-0 lg:pl-8">
          <UpdatesFeed />
          <UpcomingEvents />
        </div>
      </div>
    </main>
  );
}
