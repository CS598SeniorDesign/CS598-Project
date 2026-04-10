"use client";
import React, { useState } from "react";
import "@/style/auth.css"; // import the CSS

interface CollapsiblePanelProps {
  title: string;
  children: React.ReactNode;
}

export default function CollapsiblePanel({ title, children }: CollapsiblePanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="collapsible-panel">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="collapsible-panel-button"
      >
        {title}
        <span className="collapsible-panel-arrow">{isOpen ? "▲" : "▼"}</span>
      </button>

      {isOpen && <div className="collapsible-panel-content">{children}</div>}
    </div>
  );
}