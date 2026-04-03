"use client";
import { useState } from "react";
import Image from "next/image";

type AvatarPickerProps = {
  onSelect: (avatar: string) => void;
  selected?: string;
};

const avatars = [
  "/avatars/avatar1.webp",
  "/avatars/avatar2.webp",
  "/avatars/avatar3.webp",
  "/avatars/avatar4.webp",
  "/avatars/avatar5.webp",
  "/avatars/brandon.webp",
  "/avatars/sydney.webp",
  "/avatars/jennifer.webp",
  "/avatars/supriya.webp",
];

export default function AvatarPicker({ onSelect, selected }: AvatarPickerProps) {
  return (
    <div className="flex gap-4">
      {avatars.map((av) => (
        <div
          key={av}
          className={`cursor-pointer border-2 rounded-full p-1 ${
            selected === av ? "border-indigo-500" : "border-transparent"
          }`}
          onClick={() => onSelect(av)}
        >
          <Image src={av} alt="avatar" width={50} height={50} className="rounded-full" />
        </div>
      ))}
    </div>
  );
}