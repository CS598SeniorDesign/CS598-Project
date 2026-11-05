"use client";

import { SORT_OPTIONS, type Ownership, type PlayedFilter } from "@/lib/library";

interface LibraryToolbarProps {
  ownership: Ownership;
  search: string;
  played: PlayedFilter;
  ordering: string;
  onSearchChange: (value: string) => void;
  onPlayedChange: (value: PlayedFilter) => void;
  onOrderingChange: (value: string) => void;
}

const PLAYED_OPTIONS: { value: PlayedFilter; label: string }[] = [
  { value: "all", label: "All games" },
  { value: "played", label: "Played" },
  { value: "unplayed", label: "Not played yet" },
];

const SELECT =
  "rounded-full border border-gray-700 bg-[#1E293B] px-4 py-3 text-sm text-white outline-none focus:border-[#4F46E5]";

/** Search, the played filter and the sort order for the library list. */
export default function LibraryToolbar({
  ownership,
  search,
  played,
  ordering,
  onSearchChange,
  onPlayedChange,
  onOrderingChange,
}: LibraryToolbarProps) {
  const isWishlist = ownership === "WISHLISTED";

  return (
    <div className="mb-8 flex flex-wrap items-center gap-4">
      <input
        type="search"
        aria-label={
          isWishlist ? "Search your wishlist" : "Search your collection"
        }
        placeholder={
          isWishlist ? "Search your wishlist..." : "Search your collection..."
        }
        value={search}
        onChange={(event) => onSearchChange(event.target.value)}
        className="w-full max-w-md rounded-full border border-gray-700 bg-[#1E293B] px-5 py-3 text-white outline-none focus:border-[#4F46E5]"
      />

      <select
        aria-label="Filter by played"
        value={played}
        onChange={(event) => onPlayedChange(event.target.value as PlayedFilter)}
        className={SELECT}
      >
        {PLAYED_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <select
        aria-label="Sort by"
        value={ordering}
        onChange={(event) => onOrderingChange(event.target.value)}
        className={SELECT}
      >
        {SORT_OPTIONS[ownership].map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
