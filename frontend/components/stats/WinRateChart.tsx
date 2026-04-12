"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

type WinRateChartProps = {
  className?: string;
  data?: { label: string; value: number }[];
};

export default function WinRateChart({ className, data: customData }: WinRateChartProps) {
  const chartData = customData || [
    { label: "Wins", value: 12 },
    { label: "Losses", value: 8 },
  ];

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="label"   // 👈 IMPORTANT
            outerRadius={80}
            innerRadius={40}
            paddingAngle={2}
          >
            <Cell fill="#10B981" />
            <Cell fill="#EF4444" />
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}