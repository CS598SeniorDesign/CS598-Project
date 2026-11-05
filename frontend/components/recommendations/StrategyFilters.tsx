"use client";

import type { Choice } from "@/lib/recommendations";

/** Filter values for the strategies listed on the Discover tab. */
export interface StrategyFilterValues {
  period?: string;
  year?: number;
  days?: number;
}

interface StrategyFiltersProps {
  /** The active strategy's parameters, from /recommendations/options/. */
  parameters: string[];
  periods: Choice[];
  values: StrategyFilterValues;
  onChange: (values: StrategyFilterValues) => void;
}

const DAY_OPTIONS: Choice[] = [
  { key: "30", label: "Past month" },
  { key: "90", label: "Past 3 months" },
  { key: "180", label: "Past 6 months" },
  { key: "365", label: "Past year" },
];

const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS: Choice[] = Array.from({ length: 6 }, (_, index) => {
  const year = String(CURRENT_YEAR - index);
  return { key: year, label: year };
});

function FilterSelect({
  label,
  value,
  choices,
  blankLabel,
  onChange,
}: {
  label: string;
  value: string;
  choices: Choice[];
  /** Label for the empty option; leave out to offer no empty option. */
  blankLabel?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm text-gray-400">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-lg border border-gray-700 bg-slate-800 p-2"
      >
        {blankLabel !== undefined && <option value="">{blankLabel}</option>}
        {choices.map((choice) => (
          <option key={choice.key} value={choice.key}>
            {choice.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function toNumber(value: string): number | undefined {
  return value ? Number(value) : undefined;
}

function toText(value: number | undefined): string {
  return value === undefined ? "" : String(value);
}

/**
 * The filters a strategy accepts: a look-back period or a calendar year for
 * "Most popular", and a number of days for the recent-play strategies. The
 * backend rejects period and year together, so picking one clears the other,
 * and it defaults to the past month when neither is given.
 */
export default function StrategyFilters({
  parameters,
  periods,
  values,
  onChange,
}: StrategyFiltersProps) {
  const usingYear = values.year !== undefined;
  const filters = [
    parameters.includes("period") && (
      <FilterSelect
        key="period"
        label="Popular over"
        value={usingYear ? "" : (values.period ?? "month")}
        choices={periods}
        blankLabel={usingYear ? "—" : undefined}
        onChange={(period) => onChange({ period: period || undefined })}
      />
    ),
    parameters.includes("year") && (
      <FilterSelect
        key="year"
        label="Or during year"
        value={toText(values.year)}
        choices={YEAR_OPTIONS}
        blankLabel="Any year"
        onChange={(year) => onChange({ year: toNumber(year) })}
      />
    ),
    parameters.includes("days") && (
      <FilterSelect
        key="days"
        label="Looking back"
        value={toText(values.days)}
        choices={DAY_OPTIONS}
        blankLabel="Default"
        onChange={(days) => onChange({ days: toNumber(days) })}
      />
    ),
  ].filter(Boolean);

  if (filters.length === 0) return null;

  return <div className="mt-4 flex flex-wrap items-end gap-4">{filters}</div>;
}
