"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip
} from "recharts";

const data = [
  { name: "Wins", value: 12 },
  { name: "Losses", value: 8 }
];

export default function WinRateChart() {

  return (

    <PieChart width={300} height={300}>

      <Pie
        data={data}
        dataKey="value"
        outerRadius={100}
      >
        <Cell fill="#10B981" />
        <Cell fill="#EF4444" />
      </Pie>

      <Tooltip />

    </PieChart>

  );
}