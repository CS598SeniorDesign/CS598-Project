import Image from "next/image";
import NotificationIcon from "./NotificationIcon";

const groups = [
  {
    name: "Dungeon Dwellers",
    avatar: "/avatars/group1.webp",
  },
  {
    name: "Main Disaster Women",
    avatar: "/avatars/group2.webp",
  },
  {
    name: "The A-Team",
    avatar: "/avatars/group3.webp",
  },
];

export default function GameGroups() {
  return (
    <div>
      <h2 className="text-3xl font-bold mb-6 tracking-wide">
        YOUR GAME GROUPS
      </h2>

      <div className="flex items-start justify-between">
        <ul className="space-y-6">
          {groups.map((group) => (
            <li key={group.name} className="flex items-center gap-4 text-2xl">
              <Image
                src={group.avatar}
                alt={group.name}
                width={56}
                height={56}
                className="rounded-full object-cover border border-gray-500"
              />
              <span>{group.name}</span>
            </li>
          ))}
        </ul>

        <div className="mt-20 mr-4">
          <NotificationIcon />
        </div>
      </div>
    </div>
  );
}