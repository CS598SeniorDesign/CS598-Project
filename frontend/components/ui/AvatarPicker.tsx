"use client";
import { useState } from "react";
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
  "/avatars/brandon.webp",
  "/avatars/sydney.webp",
  "/avatars/jennifer.webp",
  "/avatars/supriya.webp",
];

export default function AvatarPicker({ onSelect, selected }: AvatarPickerProps) {
  return (
    <div className="flex flex-wrap gap-5 justify-center">
      {AVATARS.map((av) => (
        <div
          key={av}
          className={`cursor-pointer transition-all duration-200 border-2 rounded-full p-1 hover:scale-110 ${
            selected === av ? "ring-4 ring-border-indigo-500 scale-110" : "ring-2 ring-transparent hover:ring-gray-500"
          }`}
          onClick={() => onSelect(av)}
        >
          <Image src={av} alt="avatar" width={50} height={50} className="rounded-full" />
        </div>
      ))}
    </div>
  );
}