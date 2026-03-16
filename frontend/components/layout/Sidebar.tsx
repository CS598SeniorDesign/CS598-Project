import Link from "next/link";

export default function Sidebar() {

  return (
    <div className="
      w-64
      bg-slate-900
      h-screen
      p-6
      border-r
      border-gray-700
    ">

      <h2 className="text-2xl font-bold mb-10">
        QuestLog
      </h2>

      <nav className="flex flex-col gap-4">

        <Link href="/dashboard">
          Dashboard
        </Link>

        <Link href="/games/search">
          Search Games
        </Link>

        <Link href="/profile">
          Profile
        </Link>

      </nav>

    </div>
  );
}