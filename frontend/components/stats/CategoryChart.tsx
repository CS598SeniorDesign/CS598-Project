"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const data = [
  { category: "Strategy", games: 5, color: "#E11D48" },
  { category: "Party", games: 6, color: "#DB2777" },
  { category: "Deck", games: 5, color: "#60A5FA" },
  { category: "Co-op", games: 3, color: "#34D399" },
  { category: "Deduction", games: 2, color: "#A78BFA" },
  { category: "Worker", games: 4, color: "#C084FC" },
];

export default function CategoryChart() {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <XAxis
          dataKey="category"
          tick={{ fill: "#CBD5E1", fontSize: 12 }}
        />
        <YAxis tick={{ fill: "#CBD5E1" }} />
        <Tooltip />
        <Bar dataKey="games" radius={[8, 8, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}