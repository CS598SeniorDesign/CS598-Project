interface BadgeProps {
  label: string
  color?: "primary" | "secondary" | "accent"
}

export default function Badge({
  label,
  color = "primary",
}: BadgeProps) {
  const colors = {
    primary: "bg-indigo-600",
    secondary: "bg-emerald-600",
    accent: "bg-amber-500 text-black",
  }

  return (
    <span
      className={`px-3 py-1 text-sm rounded-full text-white ${colors[color]}`}
    >
      {label}
    </span>
  )
}