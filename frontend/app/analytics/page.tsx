"use client";

import WinRateChart from "@/components/stats/WinRateChart";
import React from "react";

export default function AnalyticsPage() {
  return (
    <div className="min-h-screen bg-[#0F172A] text-[#F8FAFC] p-8">
      <h1 className="text-4xl font-bold mb-2">Your Analytics</h1>
      <p className="text-gray-400 mb-8">
        View your gameplay, win/loss rates and activity
      </p>

        {/* STATS */}
         <div className="bg-[#1E293B]/70 p-5 rounded-2xl text-center shadow-lg">
          <h2 className="mb-4">Your Stats</h2>

          <div className="flex justify-around mb-6">
           <div>
             <p className="text-gray-400 text-sm">Total Plays</p>
             <p className="text-2xl font-bold text-indigo-400">58</p>
             <p className="text-xs text-green-400">+11 this month</p>
           </div>

           <div>
             <p className="text-gray-400 text-sm">Win Rate</p>
             <p className="text-2xl font-bold text-indigo-400">71%</p>
             <p className="text-xs text-green-400">+6% improvement</p>
           </div>

           <div>
             <p className="text-gray-400 text-sm">Owned</p>
             <p className="text-2xl font-bold text-indigo-400">24</p>
             <p className="text-xs text-green-400">+2 new</p>
           </div>
         </div>
        </div>

      {/* CHARTS */}
       <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">

       {/* WIN RATE */}
       <div className="bg-[#1E293B] p-6 rounded-xl h-[350px]">
         <h2 className="mb-2 text-center">Win Rate</h2>
         <div className="flex-1 flex items-center justify-center">
          <WinRateChart className="w-full h-full" />
         </div>
       </div>

       {/* DONUT */}
       <div className="bg-[#1E293B] p-6 rounded-xl flex flex-col items-center justify-center">
         <h2 className="mb-3">Game Types</h2>
       
         <div
          className="w-40 h-40 rounded-full relative"
          style={{
            background:
              "conic-gradient(#4F46E5 40%, #10B981 25%, #FFBF00 20%, #EF4444 15%)",
          }}
        >
          <div className="absolute inset-6 bg-[#0F172A] rounded-full" />
        </div>

         <p className="text-gray-400 text-sm mt-2 text-center">
            Strategy • Party • Co-op • Family
         </p>
        </div>

       </div>
    </div>
    );
}