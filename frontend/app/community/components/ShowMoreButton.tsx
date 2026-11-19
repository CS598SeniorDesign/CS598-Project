"use client";

import { ChevronDown, ChevronUp } from "lucide-react";

type ShowMoreButtonProps = {
  expanded: boolean;
  total: number;
  initialVisible: number;
  onToggle: () => void;
};

export default function ShowMoreButton({
  expanded,
  total,
  initialVisible,
  onToggle,
}: ShowMoreButtonProps) {
  if (total <= initialVisible) {
    return null;
  }

  const remaining = total - initialVisible;

  return (
    <button
      type="button"
      aria-expanded={expanded}
      onClick={onToggle}
      className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-surface px-4 py-3 text-sm font-semibold text-link transition-colors hover:border-indigo-500/40 hover:bg-surface-hover"
    >
      {expanded ? (
        <>
          Show Less
          <ChevronUp className="h-4 w-4" />
        </>
      ) : (
        <>
          Show More ({remaining} more)
          <ChevronDown className="h-4 w-4" />
        </>
      )}
    </button>
  );
}
