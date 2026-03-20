export default function Page() {
  type Game = {
    name: string;
    img: string;
  };

  type Play = {
    name: string;
    img: string;
    result: "Won" | "Lost";
    players: number;
    time: string;
    date: string;
  };

  type CommunityItem = {
    name: string;
    img: string;
  };

  const games: Game[] = [
    { name: "Botany", img: "/images/botany.webp" },
    { name: "Stardew Valley", img: "/images/stardew.webp" },
    { name: "Pandemic", img: "/images/pandemic.webp" },
    { name: "Root", img: "/images/root.webp" },
    { name: "Catan", img: "/images/catan.webp"},
  ];

  const recentPlays: Play[] = [
    {
      name: "Terraforming Mars",
      img: "/images/terraforming.webp",
      result: "Won",
      players: 3,
      time: "90 min",
      date: "Feb 22",
    },
    {
      name: "Catan",
      img: "/images/catan.webp",
      result: "Lost",
      players: 4,
      time: "60 min",
      date: "March 11",
    },
    {
      name: "Azul",
      img: "/images/azul.webp",
      result: "Won",
      players: 3,
      time: "30 min",
      date: "January 21",
    },
  ];

  const community: CommunityItem[] = [
    { name: "Terraforming Mars", img: "/images/terraforming.webp" },
    { name: "Catan", img: "/images/catan.webp" },
    { name: "Everdell", img: "/images/everdell.webp" },
  ];

  const days: string[] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <div className="min-h-screen bg-[#0F172A] text-[#F8FAFC]">
      {/* NAVBAR */}
      <div className="flex justify-between items-center px-8 py-4 bg-gradient-to-r from-[#1E293B] to-[#0F172A] shadow-xl">
        <h1 className="text-xl font-bold">QuestLog</h1>

        <div className="flex gap-10 text-gray-300">
          <p className="border-b-2 border-[#4F46E5] pb-1 cursor-pointer">
            Game Library
          </p>
          <p className="hover:text-white cursor-pointer transition">
            Recommendations for you
          </p>
          <p className="hover:text-white cursor-pointer transition">
            Weeple
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gray-500 rounded-full" />
          <p>MeepleTeam</p>
        </div>
      </div>

      <div className="p-8">
        {/* TITLE */}
        <h1 className="text-3xl font-bold">Welcome to QuestLog by the Meeple</h1>
        <p className="text-gray-400 mb-6">Your shared activity hub</p>

        {/* TOP ROW */}
        <div className="grid grid-cols-3 gap-6">
          {/* RECENT GROUP GAMES */}
          <div className="col-span-2 bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg hover:shadow-xl transition">
            <h2 className="mb-4 text-gray-300">Recent Group Games</h2>

            <div className="flex gap-5">
              {games.map((game, i) => (
                <div key={i} className="w-44">
                  <img
                    src={game.img}
                    className="rounded-xl mb-2 h-40 w-full object-cover hover:scale-105 hover:shadow-[0_0_20px_rgba(79,70,229,0.4)] transition"
                  />
                  <p className="text-sm font-semibold">{game.name}</p>
                  <div className="text-[#FFBF00] text-sm">★★★★★</div>
                </div>
              ))}
            </div>
          </div>

          {/* CALENDAR */}
          <div className="bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg">
            <h2 className="mb-2 text-gray-300">Calendar</h2>
            <h3 className="text-center mb-3 font-semibold tracking-wide">
              FEBRUARY
            </h3>

            {/* Days */}
            <div className="grid grid-cols-7 text-xs text-gray-400 mb-2 text-center">
              {days.map((d) => (
                <div key={d}>{d}</div>
              ))}
            </div>

            {/* Dates */}
            <div className="grid grid-cols-7 gap-2 text-sm text-center">
              {[...Array(31)].map((_, i) => (
                <div
                  key={i}
                  className="h-10 flex items-center justify-center rounded-lg bg-[#0F172A] hover:bg-[#4F46E5] transition relative"
                >
                  {i + 1}

                  {(i === 9 || i === 22) && (
                    <div className="absolute bottom-1 text-[9px] bg-[#10B981] px-1 rounded">
                      Game
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* MIDDLE ROW */}
        <div className="grid grid-cols-3 gap-6 mt-6">
          {/* RECENT PLAYS */}
          <div className="bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg">
            <h2 className="mb-3">Recently Played</h2>

            {recentPlays.map((play, i) => (
              <div
                key={i}
                className="flex gap-3 bg-[#0F172A] p-3 rounded-lg mb-2"
              >
                <img
                  src={play.img}
                  className="w-12 h-12 rounded-lg object-cover"
                />

                <div className="flex-1">
                  <p className="text-sm font-semibold">{play.name}</p>
                  <p className="text-xs text-gray-400">
                    {play.date} | {play.players} Players | {play.time}
                  </p>
                </div>

                <span
                  className={`text-sm font-semibold ${
                    play.result === "Won"
                      ? "text-[#10B981]"
                      : "text-[#EF4444]"
                  }`}
                >
                  {play.result}
                </span>
              </div>
            ))}
          </div>

          {/* STATS */}
          <div className="bg-[#1E293B]/70 p-5 rounded-2xl text-center shadow-lg">
            <h2 className="mb-4">Your Stats</h2>

            <div className="flex justify-around">
              <div>
                <p className="text-gray-400 text-3xl font-bold">Total Plays</p>
                <p className="text-2xl font-bold">58</p>
              </div>
              <div>
                <p className="text-gray-400 text-3xl font-bold">Win Rate</p>
                <p className="text-2xl font-bold text-[#10B981]">71%</p>
              </div>
              <div>
                <p className="text-gray-400 text-3xl font-bold">Owned</p>
                <p className="text-2xl font-bold">19</p>
              </div>
            </div>
          </div>

          {/* COMMUNITY */}
          <div className="bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg">
            <h2 className="mb-3">Weeple Community Feed</h2>

            {community.map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-3 bg-[#0F172A] p-2 rounded-lg mb-2"
              >
                <img src={item.img} className="w-10 h-10 rounded" />
                <span className="text-sm">{item.name}</span>
                <span className="ml-auto text-xs bg-[#4F46E5] px-2 py-1 rounded">
                  Game Night
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* BOTTOM ROW */}
        <div className="grid grid-cols-2 gap-6 mt-6">
          {/* MEMBERS */}
          <div className="bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg">
            <h2 className="mb-3">Members</h2>

            {["Brandon", "Jennifer", "Sydney", "Supriya"].map((m) => (
              <div
                key={m}
                className="flex justify-between bg-[#0F172A] p-2 rounded-lg mb-2"
              >
                <span>{m}</span>
                <span className="text-[#FFBF00] text-xs">Tag</span>
              </div>
            ))}
          </div>

          {/* DONUT */}
          <div className="bg-[#1E293B]/70 p-5 rounded-2xl shadow-lg flex flex-col items-center">
            <h2 className="mb-3">Game Types</h2>

            <div
              className="w-40 h-40 rounded-full relative"
              style={{
                background:
                  "conic-gradient(#4F46E5 40%, #10B981 25%, #FFBF00 20%, #EF4444 15%)",
              }}
            >
              <div className="absolute inset-6 bg-[#0F172A] rounded-full" />
            </div>

            <p className="text-gray-400 text-sm mt-2 text-center">
              Strategy • Party • Co-op • Family
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}