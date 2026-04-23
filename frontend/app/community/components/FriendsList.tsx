import Image from "next/image";

const friends = [
  {
    name: "1Meekat",
    avatar: "/avatars/friend1.webp",
  },
  {
    name: "Whirelwindd",
    avatar: "/avatars/friend2.webp",
  },
  {
    name: "Katatsu",
    avatar: "/avatars/friend3.webp",
  },
  {
    name: "LindaaCutiek",
    avatar: "/avatars/frienda.webp",
  },
  {
    name: "Rononoa",
    avatar: "/avatars/friend5.webp",
  }
];

export default function FriendsList() {
  return (
    <div className="pt-6 border-t border-gray-500">
      <h2 className="text-3xl font-bold mb-6 tracking-wide">
        YOUR FRIENDS
      </h2>

      <ul className="space-y-6">
        {friends.map((friend) => (
          <li
            key={friend.name}
            className="flex items-center gap-4 text-2xl"
          >
            <Image
              src={friend.avatar}
              alt={friend.name}
              width={56}
              height={56}
              className="rounded-full object-cover border border-gray-500"
            />
            <span className="font-medium">{friend.name}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}