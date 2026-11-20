"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

type WinRateChartProps = {
  className?: string;
  data?: { label: string; value: number }[];
};

export default function WinRateChart({
  className,
  data: customData,
}: WinRateChartProps) {
  const chartData = customData || [
    { label: "Wins", value: 12 },
    { label: "Losses", value: 8 },
  ];

  return (
    <div className={className}>
      <div className="h-[300px] w-full max-w-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="label"
              outerRadius={100}
              innerRadius={60}
              paddingAngle={2}
              stroke="var(--surface)"
              strokeWidth={2}
            >
              <Cell fill="#10B981" />
              <Cell fill="#EF4444" />
            </Pie>

            <Tooltip
              contentStyle={{
                backgroundColor: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                color: "var(--foreground)",
              }}
              labelStyle={{
                color: "var(--foreground)",
              }}
              itemStyle={{
                color: "var(--foreground)",
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
