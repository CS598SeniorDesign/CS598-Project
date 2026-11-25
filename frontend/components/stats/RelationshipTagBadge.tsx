import {
  CalendarCheck,
  Clover,
  Ghost,
  Handshake,
  Hourglass,
  Scale,
  Skull,
  Swords,
  Target,
  type LucideIcon,
} from "lucide-react";
import type { RelationshipTag, RelationshipTagType } from "@/lib/analytics";

/**
 * Colour and icon for each tag. Class names are written out in full so
 * Tailwind can find them.
 */
const TAG_STYLES: Record<
  RelationshipTagType,
  { icon: LucideIcon; className: string }
> = {
  MORTAL_ENEMY: {
    icon: Swords,
    className:
      "border-red-500/40 bg-red-500/10 text-red-200 [html[data-theme=light]_&]:text-red-700",
  },
  PUNCHING_BAG: {
    icon: Target,
    className:
      "border-amber-500/40 bg-amber-500/10 text-amber-200 [html[data-theme=light]_&]:text-amber-800",
  },
  RIVAL: {
    icon: Scale,
    className:
      "border-orange-500/40 bg-orange-500/10 text-orange-200 [html[data-theme=light]_&]:text-orange-800",
  },
  SIDEKICK: {
    icon: Handshake,
    className:
      "border-emerald-500/40 bg-emerald-500/10 text-emerald-200 [html[data-theme=light]_&]:text-emerald-700",
  },
  DOOMED_DUO: {
    icon: Skull,
    className:
      "border-slate-400/40 bg-slate-500/10 text-slate-200 [html[data-theme=light]_&]:text-slate-700",
  },
  REGULAR: {
    icon: CalendarCheck,
    className:
      "border-indigo-500/40 bg-indigo-500/10 text-indigo-200 [html[data-theme=light]_&]:text-indigo-700",
  },
  LUCKY_CHARM: {
    icon: Clover,
    className:
      "border-teal-500/40 bg-teal-500/10 text-teal-200 [html[data-theme=light]_&]:text-teal-700",
  },
  JINX: {
    icon: Ghost,
    className:
      "border-purple-500/40 bg-purple-500/10 text-purple-200 [html[data-theme=light]_&]:text-purple-700",
  },
  LONG_TIME_NO_SEE: {
    icon: Hourglass,
    className:
      "border-sky-500/40 bg-sky-500/10 text-sky-200 [html[data-theme=light]_&]:text-sky-700",
  },
};

export function RelationshipTagBadge({
  tag,
  compact = false,
}: {
  tag: RelationshipTag;
  compact?: boolean;
}) {
  const { icon: Icon, className } = TAG_STYLES[tag.tag_type];
  const sizeClass = compact
    ? "gap-1 px-2 py-0.5 text-[11px]"
    : "gap-1 px-3 py-1 text-xs";

  return (
    <span
      title={tag.description}
      aria-label={`${tag.name}: ${tag.description}`}
      className={`inline-flex items-center rounded-full border font-medium ${sizeClass} ${className}`}
    >
      <Icon aria-hidden="true" className={compact ? "h-3 w-3" : "h-4 w-4"} />
      {tag.name}
    </span>
  );
}

/** A friend's tags as a row of badges; renders nothing when there are none. */
export function RelationshipTagList({
  tags = [],
  compact = false,
}: {
  tags?: RelationshipTag[];
  compact?: boolean;
}) {
  if (tags.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((tag) => (
        <RelationshipTagBadge key={tag.tag_type} tag={tag} compact={compact} />
      ))}
    </div>
  );
}
