"use client";

import { useId } from "react";
import { MAX_SCORE, MIN_SCORE } from "@/lib/ratings";

interface StarInputProps {
  label: string;
  hint?: string;
  /** The chosen score, or 0 when none is chosen yet. */
  value: number;
  disabled?: boolean;
  onChange: (value: number) => void;
}

const SCORES = Array.from(
  { length: MAX_SCORE - MIN_SCORE + 1 },
  (_, index) => MIN_SCORE + index,
);

/**
 * A 1-5 star picker. It is a radio group, so it works with the keyboard
 * (arrow keys move between stars) and screen readers.
 */
export default function StarInput({
  label,
  hint,
  value,
  disabled = false,
  onChange,
}: StarInputProps) {
  // Unique per instance, so two editors on one page don't share a radio group.
  const name = useId();

  return (
    <fieldset
      disabled={disabled}
      className="flex items-center justify-between gap-4"
    >
      <legend className="sr-only">{label}</legend>
      <div aria-hidden="true">
        <p className="text-sm font-semibold">{label}</p>
        {hint && <p className="text-xs text-gray-400">{hint}</p>}
      </div>

      <div className="flex">
        {SCORES.map((score) => (
          <label
            key={score}
            className="cursor-pointer px-0.5 text-2xl leading-none"
          >
            <input
              type="radio"
              name={name}
              value={score}
              checked={value === score}
              onChange={() => onChange(score)}
              aria-label={`${score} ${score === 1 ? "star" : "stars"}`}
              className="peer sr-only"
            />
            <span
              aria-hidden="true"
              className={`rounded transition peer-focus-visible:ring-2 peer-focus-visible:ring-indigo-400 ${
                score <= value
                  ? "text-[#FACC15]"
                  : "text-gray-600 hover:text-gray-400"
              }`}
            >
              ★
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
