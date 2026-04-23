"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

const data = [
  { name: "Brandon", value: 42, color: "#DC2626" },
  { name: "Jennifer", value: 28, color: "#F97316" },
  { name: "Sydney", value: 18, color: "#FACC15" },
  { name: "Supriya", value: 12, color: "#3B82F6" },
];

export default function PlayerPieChart() {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={90}
          label
        >
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}