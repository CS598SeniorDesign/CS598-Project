import Image from "next/image";

const updates = [
  {
    avatar: "/avatars/friend1.webp",
    content: (
      <>
        1Meekat rated <span className="underline">Hues and Cues</span>
        <span className="ml-3 text-yellow-400">★★★★★</span>
      </>
    ),
  },
  {
    avatar: "/avatars/friend2.webp",
    content: (
      <>
        Whirelwindd added <span className="underline">Skyteam</span> to their
        wishlist
      </>
    ),
  },
 {
    avatar: "/avatars/frienda.webp",
    content: (
      <>
        LindaaCutiek created a new event in
        <span className="underline ml-1">Dungeon Dwellers</span>
      </>
    ),
  },
  {
    avatar: "/avatars/group2.webp",
    content: (
      <>
        Upcoming event in
        <span className="underline ml-1">Main Disaster Women</span>
      </>
    ),
  },
  {
    avatar: "/avatars/friend3.webp",
    content: (
      <>
        Katatsu is now “The Collector” in
        <span className="underline ml-1">Dungeon Dwellers</span>
      </>
    ),
  },
    {
    avatar: "/avatars/friend2.webp",
    content: (
      <>
        Whirelwindd reviewed
        <span className="underline ml-1">Slay The Spire</span>
      </>
    ),
  },
   {
    avatar: "/avatars/friend5.webp",
    content: (
      <>
        Rononoa reviewed
        <span className="underline ml-1">Slay The Spire</span>
      </>
    ),
  },
];
export default function UpdatesFeed() {
  return (
    <div>
      <h2 className="text-3xl font-bold mb-6 tracking-wide">
        RECENT UPDATES
      </h2>

      <ul className="space-y-7">
        {updates.map((update, index) => (
          <li key={index} className="flex items-start gap-4 text-2xl leading-8">
            <Image
              src={update.avatar}
              alt="avatar"
              width={56}
              height={56}
              className="w-14 h-14 rounded-full object-cover border border-gray-500 mt-1"
            />

            <div>{update.content}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}