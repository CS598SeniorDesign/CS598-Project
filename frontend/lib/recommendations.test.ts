import {
  buildRecommendationQuery,
  fetchRecommendationFeedback,
  fetchRecommendations,
  RecommendationApiError,
  removeRecommendationFeedback,
  sendRecommendationFeedback,
} from "./recommendations";

const mockFetch = jest.fn();

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

beforeEach(() => {
  mockFetch.mockReset();
  global.fetch = mockFetch as unknown as typeof fetch;
  document.cookie = "csrf_token=test-token";
});

describe("buildRecommendationQuery", () => {
  it("drops empty values and false flags", () => {
    expect(
      buildRecommendationQuery({
        strategy: "decision_chart",
        players: 4,
        mood: undefined,
        complexity: "",
        owned_only: false,
        period: null,
      }),
    ).toBe("strategy=decision_chart&players=4");
  });

  it("keeps true flags", () => {
    expect(buildRecommendationQuery({ owned_only: true })).toBe(
      "owned_only=true",
    );
  });
});

describe("fetchRecommendations", () => {
  it("requests the recommendations endpoint with the query", async () => {
    const body = {
      requested_strategy: "popular",
      strategy: "popular",
      personalized: false,
      fallback_reason: null,
      results: [],
    };
    mockFetch.mockResolvedValue(jsonResponse(body));

    await expect(
      fetchRecommendations({ strategy: "popular", period: "year" }),
    ).resolves.toEqual(body);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/recommendations/?strategy=popular&period=year",
      expect.objectContaining({ method: "GET", credentials: "same-origin" }),
    );
  });

  it("turns validation errors into a readable message", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ game_id: ["This strategy needs a game."] }, 400),
    );

    await expect(
      fetchRecommendations({ strategy: "similar_games" }),
    ).rejects.toThrow("This strategy needs a game.");
  });

  it("explains throttling", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "slow down" }, 429));

    const error = await fetchRecommendations({}).catch((err) => err);
    expect(error).toBeInstanceOf(RecommendationApiError);
    expect(error.status).toBe(429);
    expect(error.message).toMatch(/too quickly/);
  });
});

describe("feedback", () => {
  it("sends likes with the CSRF token", async () => {
    mockFetch.mockResolvedValue(jsonResponse({}, 201));

    await sendRecommendationFeedback(13, "LIKE", "for_you");

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/v1/recommendations/feedback/");
    expect(init.method).toBe("POST");
    expect(init.headers["X-CSRFToken"]).toBe("test-token");
    expect(JSON.parse(init.body)).toEqual({
      game_id: 13,
      sentiment: "LIKE",
      strategy: "for_you",
    });
  });

  it("removes a reaction by BGG ID", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 204,
      json: async () => null,
    });

    await removeRecommendationFeedback(13);

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/recommendations/feedback/13/",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("reads paginated and unpaginated feedback lists", async () => {
    const item = { game: { bgg_id: 1 }, sentiment: "LIKE" };
    mockFetch.mockResolvedValueOnce(jsonResponse({ results: [item] }));
    mockFetch.mockResolvedValueOnce(jsonResponse([item]));

    await expect(fetchRecommendationFeedback()).resolves.toEqual([item]);
    await expect(fetchRecommendationFeedback()).resolves.toEqual([item]);
  });
});
