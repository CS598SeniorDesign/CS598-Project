import Link from "next/link";

const features = [
  {
    title: "Your Game Library",
    description:
      "Keep track of the board games you own, want to play, and love.",
  },
  {
    title: "Play Sessions",
    description:
      "Record your game nights, track scores, and remember your favorite moments.",
  },
  {
    title: "Game Analytics",
    description: "Explore your play history, statistics, and game performance.",
  },
  {
    title: "Weeple Community",
    description:
      "Connect with other board game enthusiasts and share your gaming experiences.",
  },
  {
    title: "Game Recommendations",
    description:
      "Discover board games that match your interests and preferences.",
  },
];

const teamMembers = [
  {
    name: "Supriya Gurung",
    role: "Frontend Lead",
    initials: "SG",
  },
  {
    name: "Jennifer Isobe",
    role: "Backend & Security",
    initials: "JI",
  },
  {
    name: "Brandon Nguyen",
    role: "Backend, Database & Analytics",
    initials: "BN",
  },
  {
    name: "Sydney Epke",
    role: "QA & Testing Lead",
    initials: "SE",
  },
];

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-background px-6 py-16 text-white">
      <div className="mx-auto max-w-5xl">
        {/* About QuestLog */}
        <section className="mb-16">
          <h1 className="mb-6 bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 bg-clip-text text-5xl font-extrabold text-transparent md:text-6xl">
            About QuestLog
          </h1>

          <p className="max-w-3xl text-lg leading-relaxed text-gray-300">
            QuestLog is your home for board game tracking, discovering new
            favorites, and connecting with fellow board game enthusiasts.
            Whether you are a casual player or a competitive strategist,
            QuestLog helps you keep your gaming adventures organized in one
            place.
          </p>
        </section>

        {/* Features */}
        <section className="mb-20">
          <h2 className="mb-8 text-3xl font-bold">
            What Can You Do With QuestLog?
          </h2>

          <div className="grid gap-6 md:grid-cols-2">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="rounded-xl border border-gray-700 bg-[#111827] p-6 transition hover:border-indigo-500"
              >
                <h3 className="mb-3 text-xl font-semibold text-purple-300">
                  {feature.title}
                </h3>

                <p className="leading-relaxed text-gray-400">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Meet the Team */}
        <section className="mb-20">
          <div className="mb-10 text-center">
            <h2 className="mb-4 text-4xl font-bold">Meet the Meeples</h2>

            <p className="mx-auto max-w-2xl leading-relaxed text-gray-400">
              QuestLog was created by The Meeples, a group of Computer Science
              students at Wichita State University, as part of our senior design
              project. We are passionate about building product that can people
              together and make board game nights even more memorable.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {teamMembers.map((member) => (
              <div
                key={member.name}
                className="rounded-xl border border-gray-700 bg-[#1E293B] p-6 text-center transition duration-200 hover:-translate-y-1 hover:border-indigo-500 hover:shadow-lg hover:shadow-indigo-500/10"
              >
                {/* Initials Avatar */}
                <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-indigo-600 text-xl font-bold text-white">
                  {member.initials}
                </div>

                <h3 className="mb-2 font-semibold text-white">{member.name}</h3>

                <p className="text-sm text-indigo-300">{member.role}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Back to Homepage */}
        <div className="text-center">
          <Link
            href="/"
            className="inline-block rounded-lg bg-primary px-8 py-3 font-medium text-white transition hover:opacity-90"
          >
            Back to Home
          </Link>
        </div>

        {/* Footer */}
        <footer className="mt-16 border-t border-gray-800 pt-6 text-center text-sm text-gray-500">
          <p>QuestLog · Team Meeples · Wichita State University · 2026</p>
        </footer>
      </div>
    </main>
  );
}
