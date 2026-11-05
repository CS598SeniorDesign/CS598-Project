"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import type {
  NamedTag,
  RecommendationOptions,
  RecommendationProfile,
} from "@/lib/recommendations";

interface RecommendationPreferencesProps {
  profile: RecommendationProfile;
  options: RecommendationOptions | null;
  onSave: (changes: Partial<RecommendationProfile>) => Promise<void>;
}

/** Complexity bands shown to users, stored as a point on BGG's 1-5 scale. */
const COMPLEXITY_POINTS = [
  { value: "", label: "No preference" },
  { value: "1.50", label: "Light" },
  { value: "2.75", label: "Medium" },
  { value: "4.00", label: "Heavy" },
];

function nearestComplexity(
  value: RecommendationProfile["preferred_complexity"],
) {
  if (value === null || value === undefined || value === "") return "";
  const number = Number(value);
  if (number < 2) return "1.50";
  if (number < 3.5) return "2.75";
  return "4.00";
}

function toNumberOrNull(value: string): number | null {
  if (value.trim() === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function TagPicker({
  legend,
  tags,
  selected,
  onToggle,
}: {
  legend: string;
  tags?: NamedTag[];
  selected: number[];
  onToggle: (id: number) => void;
}) {
  if (!tags?.length) return null;

  return (
    <fieldset className="mt-6">
      <legend className="mb-2 font-semibold">{legend}</legend>
      <div className="flex max-h-48 flex-wrap gap-2 overflow-y-auto">
        {tags.map((tag) => {
          const active = selected.includes(tag.bgg_id);
          return (
            <button
              key={tag.bgg_id}
              type="button"
              aria-pressed={active}
              onClick={() => onToggle(tag.bgg_id)}
              className={`rounded-full px-3 py-1 text-sm transition ${
                active
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-800 text-gray-300 hover:bg-slate-700"
              }`}
            >
              {tag.name}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

function NumberField({
  label,
  max,
  value,
  onChange,
}: {
  label: string;
  max: number;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm text-gray-400">{label}</span>
      <input
        type="number"
        min={1}
        max={max}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-gray-700 bg-slate-800 p-2"
      />
    </label>
  );
}

function SaveRow({
  saving,
  message,
  error,
}: {
  saving: boolean;
  message: string;
  error: string;
}) {
  return (
    <div className="mt-6 flex items-center gap-4">
      <button
        type="submit"
        disabled={saving}
        className="rounded-xl bg-indigo-600 px-6 py-2 font-semibold hover:bg-indigo-500 disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save preferences"}
      </button>
      {message && (
        <p role="status" className="text-green-400">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}

function toInputValue(value: number | null): string {
  return value === null ? "" : String(value);
}

function toggle(list: number[], id: number): number[] {
  return list.includes(id) ? list.filter((item) => item !== id) : [...list, id];
}

/**
 * Opt in to personalized recommendations and answer the onboarding questions
 * that seed them before the user has any play history.
 */
export default function RecommendationPreferences({
  profile,
  options,
  onSave,
}: RecommendationPreferencesProps) {
  const [optedIn, setOptedIn] = useState(profile.use_personal_data);
  const [categories, setCategories] = useState(profile.preferred_categories);
  const [mechanics, setMechanics] = useState(profile.preferred_mechanics);
  const [playerCount, setPlayerCount] = useState(
    toInputValue(profile.preferred_player_count),
  );
  const [playTime, setPlayTime] = useState(
    toInputValue(profile.preferred_max_play_time),
  );
  const [complexity, setComplexity] = useState(
    nearestComplexity(profile.preferred_complexity),
  );
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");

    try {
      await onSave({
        use_personal_data: optedIn,
        preferred_categories: categories,
        preferred_mechanics: mechanics,
        preferred_player_count: toNumberOrNull(playerCount),
        preferred_max_play_time: toNumberOrNull(playTime),
        preferred_complexity: complexity || null,
      });
      setMessage("Preferences saved.");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save preferences.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      aria-label="Recommendation preferences"
      className="rounded-2xl bg-gray-900 p-6"
    >
      <label className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={optedIn}
          onChange={(event) => setOptedIn(event.target.checked)}
          className="mt-1 h-5 w-5 accent-indigo-500"
        />
        <span>
          <span className="block font-semibold">
            Use my plays, library and likes to personalize recommendations
          </span>
          <span className="block text-sm text-gray-400">
            Off by default. Unlocks &quot;Recommended for you&quot;,
            &quot;Players like you enjoy&quot; and the other personal picks.
          </span>
        </span>
      </label>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <NumberField
          label="Usual player count"
          max={100}
          value={playerCount}
          onChange={setPlayerCount}
        />
        <NumberField
          label="Longest game (minutes)"
          max={1440}
          value={playTime}
          onChange={setPlayTime}
        />
        <label className="block">
          <span className="mb-1 block text-sm text-gray-400">Complexity</span>
          <select
            value={complexity}
            onChange={(event) => setComplexity(event.target.value)}
            className="w-full rounded-lg border border-gray-700 bg-slate-800 p-2"
          >
            {COMPLEXITY_POINTS.map((point) => (
              <option key={point.value} value={point.value}>
                {point.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <TagPicker
        legend="Favorite categories"
        tags={options?.categories}
        selected={categories}
        onToggle={(id) => setCategories((list) => toggle(list, id))}
      />
      <TagPicker
        legend="Favorite mechanics"
        tags={options?.mechanics}
        selected={mechanics}
        onToggle={(id) => setMechanics((list) => toggle(list, id))}
      />

      <SaveRow saving={saving} message={message} error={error} />
    </form>
  );
}
