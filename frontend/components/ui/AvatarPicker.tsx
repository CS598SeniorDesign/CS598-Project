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
    <div className="grid grid-cols-3 gap-4 sm:grid-cols-4">
      {AVATARS.map((av) => (
        <div
          key={av}
          className={`cursor-pointer rounded-full border-2 p-1 transition ${
            selected === av
              ? "border-primary bg-indigo-500/10"
              : "border-transparent hover:border-border hover:bg-surface-hover"
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
