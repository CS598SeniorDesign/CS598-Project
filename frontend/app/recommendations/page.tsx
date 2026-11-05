"use client";

import { useEffect, useState } from "react";
import DecisionChart from "@/components/recommendations/DecisionChart";
import RecommendationPreferences from "@/components/recommendations/RecommendationPreferences";
import RecommendationResults from "@/components/recommendations/RecommendationResults";
import StrategyFilters, {
  type StrategyFilterValues,
} from "@/components/recommendations/StrategyFilters";
import { useRecommendationFeedback } from "@/components/recommendations/useRecommendationFeedback";
import { useRecommendations } from "@/components/recommendations/useRecommendations";
import { decisionQuery, type DecisionAnswers } from "@/lib/decisionChart";
import {
  DEDICATED_STRATEGIES,
  fetchRecommendationOptions,
  fetchRecommendationProfile,
  updateRecommendationProfile,
  type RecommendationOptions,
  type RecommendationProfile,
  type Sentiment,
} from "@/lib/recommendations";

type Tab = "discover" | "pick" | "preferences";

const TABS: { key: Tab; label: string }[] = [
  { key: "discover", label: "Discover" },
  { key: "pick", label: "Help me pick" },
  { key: "preferences", label: "Preferences" },
];

const RESULT_LIMIT = 12;

type FeedbackHandler = (
  gameId: number,
  sentiment: Sentiment | null,
  strategy: string,
) => void;

interface TabProps {
  active: boolean;
  options: RecommendationOptions | null;
  personalized: boolean;
  feedback: Record<number, Sentiment>;
  onFeedback: FeedbackHandler;
}

function DiscoverTab({
  active,
  options,
  personalized,
  feedback,
  onFeedback,
  onOpenPreferences,
}: TabProps & { onOpenPreferences: () => void }) {
  const [strategy, setStrategy] = useState("for_you");
  const [filters, setFilters] = useState<StrategyFilterValues>({});
  const results = useRecommendations(
    active ? { strategy, limit: RESULT_LIMIT, ...filters } : null,
  );

  const strategies = (options?.strategies ?? []).filter(
    (option) => !DEDICATED_STRATEGIES.has(option.key),
  );
  const activeStrategy = strategies.find((option) => option.key === strategy);

  return (
    <section aria-label="Discover" hidden={!active}>
      <div className="flex flex-wrap gap-2">
        {strategies.map((option) => (
          <button
            key={option.key}
            type="button"
            aria-pressed={strategy === option.key}
            title={option.description}
            onClick={() => {
              setStrategy(option.key);
              setFilters({});
            }}
            className={`rounded-full px-4 py-1.5 text-sm transition ${
              strategy === option.key
                ? "bg-indigo-600 text-white"
                : "bg-slate-800 text-gray-300 hover:bg-slate-700"
            }`}
          >
            {option.label}
            {option.requires_personal_data && !personalized && " 🔒"}
          </button>
        ))}
      </div>

      {activeStrategy && (
        <>
          <p className="mt-3 text-sm text-gray-400">
            {activeStrategy.description}
          </p>
          <StrategyFilters
            parameters={activeStrategy.parameters}
            periods={options?.periods ?? []}
            values={filters}
            onChange={setFilters}
          />
        </>
      )}

      <RecommendationResults
        {...results}
        feedback={feedback}
        onFeedback={onFeedback}
        onOpenPreferences={onOpenPreferences}
      />
    </section>
  );
}

function PickTab({ active, personalized, feedback, onFeedback }: TabProps) {
  const [decision, setDecision] = useState<DecisionAnswers | null>(null);
  const results = useRecommendations(
    active && decision ? decisionQuery(decision, RESULT_LIMIT) : null,
  );

  // Kept mounted while hidden so the decision tree remembers its answers.
  return (
    <section aria-label="Help me pick" hidden={!active}>
      <DecisionChart
        personalized={personalized}
        onComplete={setDecision}
        disabled={results.loading}
      />
      {decision && (
        <RecommendationResults
          {...results}
          feedback={feedback}
          onFeedback={onFeedback}
          emptyMessage="Nothing fits all of that. Try “No preference” on one of the questions."
        />
      )}
    </section>
  );
}

/** Load the options and the user's recommendation profile once. */
function useRecommendationSetup() {
  const [options, setOptions] = useState<RecommendationOptions | null>(null);
  const [profile, setProfile] = useState<RecommendationProfile | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    Promise.all([
      fetchRecommendationOptions(controller.signal),
      fetchRecommendationProfile(controller.signal),
    ])
      .then(([loadedOptions, loadedProfile]) => {
        if (controller.signal.aborted) return;
        setOptions(loadedOptions);
        setProfile(loadedProfile);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load recommendations.",
        );
      });

    return () => controller.abort();
  }, []);

  async function saveProfile(changes: Partial<RecommendationProfile>) {
    setProfile(await updateRecommendationProfile(changes));
  }

  return { options, profile, error, saveProfile };
}

export default function RecommendationsPage() {
  const [tab, setTab] = useState<Tab>("discover");
  const { options, profile, error, saveProfile } = useRecommendationSetup();
  const { feedback, react, error: feedbackError } = useRecommendationFeedback();

  const tabProps = {
    options,
    personalized: profile?.use_personal_data ?? false,
    feedback,
    onFeedback: (gameId: number, sentiment: Sentiment | null, used: string) =>
      void react(gameId, sentiment, used),
  };

  return (
    <main className="min-h-screen bg-[#0F172A] p-8 text-[#F8FAFC]">
      <h1 className="mb-2 text-3xl font-bold">Recommendations</h1>
      <p className="mb-6 text-gray-400">
        Find your next favorite game, or let us pick one for tonight.
      </p>

      <div
        role="tablist"
        aria-label="Recommendation views"
        className="mb-6 flex gap-2 border-b border-slate-800"
      >
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={tab === item.key}
            onClick={() => setTab(item.key)}
            className={`-mb-px border-b-2 px-4 py-2 transition ${
              tab === item.key
                ? "border-indigo-500 text-white"
                : "border-transparent text-gray-400 hover:text-white"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {[error, feedbackError].filter(Boolean).map((message) => (
        <p key={message} role="alert" className="mb-4 text-red-400">
          {message}
        </p>
      ))}

      <DiscoverTab
        {...tabProps}
        active={tab === "discover"}
        onOpenPreferences={() => setTab("preferences")}
      />
      <PickTab {...tabProps} active={tab === "pick"} />

      {tab === "preferences" && profile && (
        <RecommendationPreferences
          profile={profile}
          options={options}
          onSave={saveProfile}
        />
      )}
      {tab === "preferences" && !profile && !error && (
        <p role="status" className="text-gray-400">
          Loading your preferences...
        </p>
      )}
    </main>
  );
}
