import GameGroups from "./components/GameGroups";
import FriendsList from "./components/FriendsList";
import UpdatesFeed from "./components/UpdatesFeed";

export default function CommunityPage() {
  return (
    <main className="p-6">
      
      <h1 className="text-center text-3xl font-bold mb-6 tracking-wide">
        THE WEEPLES
      </h1>

      <div className="grid grid-cols-2 gap-4 border-t border-gray-600 pt-4">

        {/* LEFT SIDE */}
        <div className="border-r border-gray-600 pr-6 space-y-6">
          <GameGroups />
          <FriendsList />
        </div>

        {/* RIGHT SIDE */}
        <div className="pl-6">
          <UpdatesFeed />
        </div>

      </div>
    </main>
  );
}