"use client";

import { useState } from "react";
import {
  answerStep,
  describeAnswers,
  getDecisionSteps,
  type DecisionAnswers,
  type DecisionOption,
} from "@/lib/decisionChart";

interface DecisionChartProps {
  /** Whether the user has opted in; adds the "only games you own" question. */
  personalized: boolean;
  /** Called with the final answers when the user finishes or skips ahead. */
  onComplete: (answers: DecisionAnswers) => void;
  disabled?: boolean;
}

/**
 * Walks the user through the decision tree one question at a time. Later
 * questions adapt to earlier answers; going back keeps answers that still fit.
 */
export default function DecisionChart({
  personalized,
  onComplete,
  disabled = false,
}: DecisionChartProps) {
  const context = { personalized };
  const [answers, setAnswers] = useState<DecisionAnswers>({});
  const [stepIndex, setStepIndex] = useState(0);

  const steps = getDecisionSteps(answers, context);
  const finished = stepIndex >= steps.length;
  const step = steps[Math.min(stepIndex, steps.length - 1)];

  function choose(option: DecisionOption) {
    const next = answerStep(answers, step.key, option.value, context);
    setAnswers(next);

    const nextIndex = stepIndex + 1;
    setStepIndex(nextIndex);
    if (nextIndex >= getDecisionSteps(next, context).length) {
      onComplete(next);
    }
  }

  function restart() {
    setAnswers({});
    setStepIndex(0);
  }

  if (finished) {
    return (
      <section
        aria-label="Your answers"
        className="rounded-2xl bg-gray-900 p-6"
      >
        <p className="text-sm text-gray-400">Picking games for</p>
        <p className="mt-1 text-lg font-semibold">
          {describeAnswers(answers, context)}
        </p>
        <div className="mt-4 flex gap-3">
          <button
            type="button"
            onClick={() => setStepIndex(steps.length - 1)}
            className="rounded-lg bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700"
          >
            ← Change last answer
          </button>
          <button
            type="button"
            onClick={restart}
            className="rounded-lg bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700"
          >
            Start over
          </button>
        </div>
      </section>
    );
  }

  const selected = answers[step.key];

  return (
    <section
      aria-label="Help me pick a game"
      className="rounded-2xl bg-gray-900 p-6"
    >
      <div className="mb-4 flex items-center justify-between text-sm text-gray-400">
        <span>
          Question {stepIndex + 1} of {steps.length}
        </span>
        {stepIndex > 0 && (
          <span className="truncate pl-4">
            {describeAnswers(answers, context)}
          </span>
        )}
      </div>

      <div
        className="mb-6 h-1.5 w-full overflow-hidden rounded-full bg-slate-800"
        aria-hidden="true"
      >
        <div
          className="h-full bg-indigo-500 transition-all"
          style={{ width: `${(stepIndex / steps.length) * 100}%` }}
        />
      </div>

      <h2 className="mb-4 text-2xl font-semibold">{step.question}</h2>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {step.options.map((option) => {
          const isSelected =
            selected !== undefined && selected === option.value;
          return (
            <button
              key={String(option.value)}
              type="button"
              disabled={disabled}
              onClick={() => choose(option)}
              className={`rounded-xl border px-4 py-3 text-left transition disabled:opacity-50 ${
                isSelected
                  ? "border-indigo-400 bg-indigo-600/30"
                  : "border-slate-700 bg-slate-800 hover:border-indigo-500"
              }`}
            >
              <span className="block font-medium">{option.label}</span>
              {option.hint && (
                <span className="block text-sm text-gray-400">
                  {option.hint}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="mt-6 flex justify-between">
        <button
          type="button"
          disabled={stepIndex === 0}
          onClick={() => setStepIndex(stepIndex - 1)}
          className="rounded-lg px-4 py-2 text-sm text-gray-300 hover:text-white disabled:invisible"
        >
          ← Back
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            setStepIndex(steps.length);
            onComplete(answers);
          }}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
        >
          Show games now
        </button>
      </div>
    </section>
  );
}
