"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { HOUSE_RULES_MAX_LENGTH } from "@/lib/library";

interface HouseRulesEditorProps {
  gameName: string;
  value: string;
  disabled?: boolean;
  onSave: (houseRules: string) => void;
}

/** Shows a game's house rules, with an inline form to edit them. */
export default function HouseRulesEditor({
  gameName,
  value,
  disabled = false,
  onSave,
}: HouseRulesEditorProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  function startEditing() {
    setDraft(value);
    setEditing(true);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSave(draft.trim());
    setEditing(false);
  }

  if (!editing) {
    return (
      <div className="text-xs">
        {value && (
          <p className="mb-1 line-clamp-3 whitespace-pre-line text-gray-300">
            <span className="font-semibold text-gray-400">House rules: </span>
            {value}
          </p>
        )}
        <button
          type="button"
          disabled={disabled}
          onClick={startEditing}
          aria-label={`${value ? "Edit" : "Add"} house rules for ${gameName}`}
          className="text-indigo-300 hover:text-indigo-200 disabled:opacity-50"
        >
          {value ? "Edit house rules" : "+ Add house rules"}
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <label className="block text-xs text-gray-400">
        House rules for {gameName}
        <textarea
          value={draft}
          maxLength={HOUSE_RULES_MAX_LENGTH}
          rows={4}
          onChange={(event) => setDraft(event.target.value)}
          className="mt-1 w-full rounded-lg border border-gray-700 bg-[#0F172A] p-2 text-sm text-white"
        />
      </label>
      <p className="text-right text-[10px] text-gray-500">
        {draft.length} / {HOUSE_RULES_MAX_LENGTH}
      </p>
      <div className="flex gap-2">
        <button
          type="submit"
          className="flex-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
        >
          Save
        </button>
        <button
          type="button"
          onClick={() => setEditing(false)}
          className="flex-1 rounded-lg bg-slate-700 px-3 py-1.5 text-xs font-semibold text-gray-200 hover:bg-slate-600"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
