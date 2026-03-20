"use client";

import { useEffect, useState } from "react";

export default function SystemFlow() {
  const [step, setStep] = useState(0);

  const steps = [
    "User Action",
    "API Request",
    "Backend Processing",
    "Database Storage",
  ];

  //  AUTO PLAY
  useEffect(() => {
    const interval = setInterval(() => {
      setStep((prev) => (prev + 1) % steps.length);
    }, 1500); // speed of animation

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#0F172A] text-[#F8FAFC] flex flex-col items-center justify-center p-6">

      <h1 className="text-3xl font-bold mb-4">
        System Flow (Live)
      </h1>

      <p className="text-gray-400 mb-10">
        Real-time request simulation
      </p>

      <div className="flex items-center space-x-6 flex-wrap justify-center">

        {steps.map((label, index) => (
          <div key={index} className="flex items-center">

            {/* Box */}
            <div
              className={`p-6 rounded-2xl shadow-lg text-center transition-all duration-500
              ${
                step === index
                  ? "bg-indigo-600 scale-110 shadow-indigo-500/50"
                  : "bg-gray-900 opacity-70"
              }`}
            >
              <p className="font-semibold">{label}</p>

              <p className="text-sm text-gray-300 mt-2">
                {index === 0 && "User logs game"}
                {index === 1 && "POST /api/play-session"}
                {index === 2 && "Django processing"}
                {index === 3 && "Stored in PostgreSQL"}
              </p>

              {step === index && (
                <p className="text-xs text-amber-300 mt-2 animate-pulse">
                  Processing...
                </p>
              )}

              {step > index && (
                <p className="text-xs text-emerald-400 mt-2">
                  ✔ Done
                </p>
              )}
            </div>

            {/* Animated Arrow */}
            {index < steps.length - 1 && (
              <span
                className={`text-2xl mx-3 transition-all duration-300
                ${
                  step === index
                    ? "text-[#FFBF00] scale-125"
                    : "text-gray-600"
                }`}
              >
                →
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Bottom badges */}
      <div className="grid grid-cols-3 gap-6 mt-12 w-full max-w-4xl">

        <div className="bg-gray-900 p-4 rounded-xl text-center">
          <p className="text-sm text-gray-400">Performance</p>
          <p className="text-emerald-400 font-semibold mt-1">
            {"< 1s API"}
          </p>
        </div>

        <div className="bg-gray-900 p-4 rounded-xl text-center">
          <p className="text-sm text-gray-400">Security</p>
          <p className="text-indigo-400 font-semibold mt-1">
            JWT Secured
          </p>
        </div>

        <div className="bg-gray-900 p-4 rounded-xl text-center">
          <p className="text-sm text-gray-400">Testing</p>
          <p className="text-amber-400 font-semibold mt-1">
            Unit • Integration • UI
          </p>
        </div>

      </div>
    </div>
  );
}