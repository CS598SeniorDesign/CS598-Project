import { Users } from "lucide-react";

export default function GameGroups() {
  return (
    <section>
      <h2 className="mb-6 text-3xl font-bold tracking-wide">
        YOUR GAME GROUPS
      </h2>

      <div className="rounded-xl border border-gray-700 bg-slate-800/40 p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-indigo-500/20">
            <Users className="h-7 w-7 text-indigo-400" />
          </div>

          <div>
            <p className="text-lg font-semibold">Game groups are coming soon</p>

            <p className="mt-2 text-sm leading-relaxed text-gray-400">
              Your game groups will appear here once group management is
              available in QuestLog.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
