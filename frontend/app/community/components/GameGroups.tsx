import NotificationIcon from "./NotificationIcon";

export default function GameGroups() {
  return (
    <div>
      <h2 className="font-bold mb-4">YOUR GAME GROUPS</h2>

      <div className="flex items-center justify-between">
        <ul className="space-y-4">
          <li className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500 rounded-full" />
            Dungeon Dwellers
          </li>

          <li className="flex items-center gap-3">
            <div className="w-8 h-8 bg-green-500 rounded-full" />
            Main Disaster Women
          </li>

          <li className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gray-400 rounded-full" />
            The A-Team
          </li>
        </ul>

        {/* Red alert icon */}
        <NotificationIcon />
      </div>
    </div>
  );
}