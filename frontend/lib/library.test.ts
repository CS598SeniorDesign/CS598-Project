import {
  addToLibrary,
  fetchLibrary,
  fetchLibraryItem,
  libraryQueryString,
  priorityLabel,
  removeFromLibrary,
  startBggCollectionSync,
  updateLibraryItem,
} from "./library";

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

describe("libraryQueryString", () => {
  it("maps the played filter to has_played and drops empty values", () => {
    expect(
      libraryQueryString({
        ownership: "OWNED",
        played: "unplayed",
        search: "  ",
        ordering: "-play_count",
      }),
    ).toBe("?ownership=OWNED&has_played=false&ordering=-play_count");
  });

  it("leaves out has_played for all games", () => {
    expect(libraryQueryString({ played: "all", search: "Catan" })).toBe(
      "?search=Catan",
    );
  });
});

describe("fetchLibrary", () => {
  it("accepts plain and paginated lists", async () => {
    const item = { game: { bgg_id: 1 } };
    mockFetch.mockResolvedValueOnce(jsonResponse([item]));
    mockFetch.mockResolvedValueOnce(jsonResponse({ results: [item] }));

    await expect(fetchLibrary()).resolves.toEqual([item]);
    await expect(fetchLibrary()).resolves.toEqual([item]);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/v1/library/");
  });

  it("asks anonymous users to log in", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "no" }, 403));

    await expect(fetchLibrary()).rejects.toThrow(
      "Please log in to view your library.",
    );
  });
});

describe("fetchLibraryItem", () => {
  it("returns null when the game is not in the library", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "Not found." }, 404));

    await expect(fetchLibraryItem(13)).resolves.toBeNull();
  });
});

describe("writes", () => {
  it("adds a game with the CSRF token", async () => {
    mockFetch.mockResolvedValue(jsonResponse({}, 201));

    await addToLibrary(13, "WISHLISTED", { wishlist_priority: 2 });

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/v1/library/");
    expect(init.method).toBe("POST");
    expect(init.headers["X-CSRFToken"]).toBe("test-token");
    expect(JSON.parse(init.body)).toEqual({
      game_id: 13,
      ownership: "WISHLISTED",
      wishlist_priority: 2,
    });
  });

  it("explains a duplicate add", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "exists" }, 409));

    await expect(addToLibrary(13, "OWNED")).rejects.toThrow(
      "This game is already in your library or wishlist.",
    );
  });

  it("patches an entry by BGG ID", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ ownership: "OWNED" }));

    await updateLibraryItem(13, { ownership: "OWNED" });

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/v1/library/13/");
    expect(init.method).toBe("PATCH");
  });

  it("shows validation messages from the backend", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(
        { wishlist_priority: ["Only wishlisted games have a priority."] },
        400,
      ),
    );

    await expect(
      updateLibraryItem(13, { wishlist_priority: 1 }),
    ).rejects.toThrow("Only wishlisted games have a priority.");
  });

  it("removes an entry", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 204,
      json: async () => null,
    });

    await expect(removeFromLibrary(13)).resolves.toBeUndefined();
    expect(mockFetch.mock.calls[0][1].method).toBe("DELETE");
  });

  it("reports a missing BGG username when starting an import", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(
        {
          detail:
            "Link a BoardGameGeek username to your profile before importing your collection.",
        },
        400,
      ),
    );

    await expect(startBggCollectionSync()).rejects.toThrow(/username/);
  });
});

describe("priorityLabel", () => {
  it("names BGG's wishlist priorities", () => {
    expect(priorityLabel(1)).toBe("Must have");
    expect(priorityLabel(null)).toBeNull();
  });
});
