export default function FriendsList() {
  return (
    <div className="pt-4 border-t border-gray-600">
      <h2 className="font-bold mb-4">YOUR FRIENDS</h2>

      <ul className="space-y-4">
        {["1Mekat", "Blackbelt55", "Gattsu", "MooseCultist"].map(name => (
          <li key={name} className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gray-500 rounded-full" />
            {name}
          </li>
        ))}
      </ul>
    </div>
  );
}