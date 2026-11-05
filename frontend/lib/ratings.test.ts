import { deleteRating, fetchRating, fetchRatings, saveRating } from "./ratings";

const mockFetch = jest.fn();

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

const scores = { experience: 4, mechanics: 3, replayability: 5, enjoyment: 4 };

beforeEach(() => {
  mockFetch.mockReset();
  global.fetch = mockFetch as unknown as typeof fetch;
  document.cookie = "csrf_token=test-token";
});

describe("fetching ratings", () => {
  it("lists the user's ratings", async () => {
    const rating = { game: { bgg_id: 13 }, ...scores, overall_rating: 4 };
    mockFetch.mockResolvedValue(jsonResponse([rating]));

    await expect(fetchRatings()).resolves.toEqual([rating]);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/v1/ratings/");
  });

  it("returns null for an unrated game", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "Not found." }, 404));

    await expect(fetchRating(13)).resolves.toBeNull();
  });
});

describe("saveRating", () => {
  it("creates a new rating", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ overall_rating: 4 }, 201));

    await saveRating(13, scores, false);

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/v1/ratings/");
    expect(init.method).toBe("POST");
    expect(init.headers["X-CSRFToken"]).toBe("test-token");
    expect(JSON.parse(init.body)).toEqual({ game_id: 13, ...scores });
  });

  it("edits an existing rating", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ overall_rating: 4 }));

    await saveRating(13, scores, true);

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/v1/ratings/13/");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual(scores);
  });

  it("switches to editing when the game was already rated", async () => {
    mockFetch
      .mockResolvedValueOnce(
        jsonResponse(
          {
            detail:
              "You have already rated Catan. Edit your existing rating instead.",
            rating_url: "http://localhost/api/v1/ratings/13/",
          },
          409,
        ),
      )
      .mockResolvedValueOnce(jsonResponse({ overall_rating: 4 }));

    await expect(saveRating(13, scores, false)).resolves.toEqual({
      overall_rating: 4,
    });
    expect(mockFetch.mock.calls[1][1].method).toBe("PATCH");
  });

  it("shows validation errors", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(
        { enjoyment: ["Ensure this value is less than or equal to 5."] },
        400,
      ),
    );

    await expect(saveRating(13, scores, true)).rejects.toThrow(
      "Ensure this value is less than or equal to 5.",
    );
  });
});

describe("deleteRating", () => {
  it("deletes by BGG ID", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 204,
      json: async () => null,
    });

    await deleteRating(13);

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/ratings/13/",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
