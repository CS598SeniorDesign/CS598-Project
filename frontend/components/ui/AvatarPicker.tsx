"use client";
import Image from "next/image";

type AvatarPickerProps = {
  onSelect: (avatar: string) => void;
  selected?: string;
};

const AVATARS = [
  "/avatars/avatar1.webp",
  "/avatars/avatar2.webp",
  "/avatars/avatar3.webp",
  "/avatars/avatar4.webp",
  "/avatars/avatar5.webp",
  "/avatars/avatar6.webp",
  "/avatars/avatar7.webp",
  "/avatars/avatar8.webp",
  "/avatars/avatar9.webp",
  "/avatars/avatar10.webp",
  "/avatars/avatar11.webp",
  "/avatars/avatar12.webp",
];

export default function AvatarPicker({
  onSelect,
  selected,
}: AvatarPickerProps) {
  return (
    <div className="grid grid-cols-3 sm:grid-cols-4 gap-4">
      {AVATARS.map((av) => (
        <div
          key={av}
          className={`cursor-pointer border-2 rounded-full p-1 ${
            selected === av ? "border-indigo-500" : "border-transparent"
          }`}
          onClick={() => onSelect(av)}
        >
          <Image
            src={av}
            alt="avatar"
            width={50}
            height={50}
            className="rounded-full"
          />
        </div>
      ))}
    </div>
  );
}
