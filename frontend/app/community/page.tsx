import GameGroups from "./components/GameGroups";
import FriendsList from "./components/FriendsList";
import UpdatesFeed from "./components/UpdatesFeed";
import TrendingThisWeek from "./components/TrendingThisWeek";
import UpcomingEvents from "./components/UpcomingEvents";

export default function CommunityPage() {
  return (
    <main className="mx-auto w-full max-w-[1500px] px-4 py-8 text-slate-100 sm:px-6 sm:py-10 lg:px-10">
      <header className="mb-8 text-center sm:mb-10">
        <h1 className="text-3xl font-extrabold tracking-[0.12em] text-white sm:text-4xl lg:text-5xl">
          THE WEEPLES
        </h1>

        <p className="mt-3 text-sm text-slate-400 sm:text-base">
          Connect, play, and share with your board gaming community.
        </p>

        <div className="mx-auto mt-5 h-0.5 w-20 rounded-full bg-indigo-500" />
      </header>

      <div className="grid grid-cols-1 items-start gap-8 border-t border-slate-700/70 pt-8 lg:grid-cols-2 lg:gap-0">
        <div className="min-w-0 space-y-9 lg:border-r lg:border-slate-700/70 lg:pr-8">
          <GameGroups />

          <FriendsList />

          <TrendingThisWeek />
        </div>

        <div className="min-w-0 space-y-9 border-t border-slate-700/70 pt-8 lg:border-t-0 lg:pt-0 lg:pl-8">
          <UpdatesFeed />

          <UpcomingEvents />
        </div>
      </div>
    </main>
  );
}
