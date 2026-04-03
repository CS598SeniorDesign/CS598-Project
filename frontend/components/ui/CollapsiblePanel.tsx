// components/ui/CollapsiblePanel.tsx
"use client";
import React, { useState } from "react";

interface CollapsiblePanelProps {
  title: string;
  children: React.ReactNode;
}

export default function CollapsiblePanel({ title, children }: CollapsiblePanelProps) {
  const [isOpen, setIsOpen] = useState(false); 

  return (
    <div className="bg-[#1E293B]/70 rounded-2xl shadow-lg mb-4 border border-gray-700">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full text-left p-4 font-semibold flex justify-between items-center hover:bg-gray-800 transition"
      >
        {title} 
        <span className="text-indigo-400">{isOpen ? "▲" : "▼"}</span>
      </button>

      {isOpen && <div className="mt-2 p-4">{children}</div>}
    </div>
  );
}