import {
  fetchGroupStatistics,
  fetchHeadToHead,
  fetchRelationshipTags,
  formatPlayDate,
  formatPlayTime,
  formatWinRate,
  tagsByFriend,
  type FriendTags,
} from "./analytics";

const mockFetch = jest.fn();

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

const friendTags: FriendTags = {
  friend: { user_id: "friend-1", display_name: "Morgan" },
  tags: [
    {
      tag_type: "MORTAL_ENEMY",
      name: "Mortal Enemy",
      description: "They have won most of the games you played together.",
      assigned_at: "2026-11-20T10:00:00Z",
    },
  ],
};

beforeEach(() => {
  mockFetch.mockReset();
  global.fetch = mockFetch as unknown as typeof fetch;
});

describe("fetchHeadToHead", () => {
  it("requests the record against the player", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ sessions_together: 3 }));

    await expect(fetchHeadToHead("user 1")).resolves.toEqual({
      sessions_together: 3,
    });
    expect(mockFetch.mock.calls[0][0]).toBe(
      "/api/v1/analytics/head-to-head/user%201/",
    );
  });

  it("explains a player who cannot be compared against", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "Not found." }, 404));

    await expect(fetchHeadToHead("user-1")).rejects.toThrow(
      "No statistics are available for this player.",
    );
  });

  it("asks the user to log in when signed out", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "No." }, 403));

    await expect(fetchHeadToHead("user-1")).rejects.toThrow(
      "Please log in to view statistics.",
    );
  });
});

describe("fetchGroupStatistics", () => {
  it("requests the group's statistics", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ total_sessions: 4 }));

    await fetchGroupStatistics(7);

    expect(mockFetch.mock.calls[0][0]).toBe("/api/v1/analytics/groups/7/");
  });

  it("explains a group the user cannot see", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "Not found." }, 404));

    await expect(fetchGroupStatistics(7)).rejects.toThrow(
      "Statistics for this group are not available.",
    );
  });

  it("falls back to a general message for other failures", async () => {
    mockFetch.mockResolvedValue(jsonResponse(null, 500));

    await expect(fetchGroupStatistics(7)).rejects.toThrow(
      "Unable to load statistics. Please try again.",
    );
  });
});

describe("fetchRelationshipTags", () => {
  it("lists every friend's tags", async () => {
    mockFetch.mockResolvedValue(jsonResponse([friendTags]));

    await expect(fetchRelationshipTags()).resolves.toEqual([friendTags]);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/v1/analytics/tags/");
  });

  it("can ask for one friend's tags", async () => {
    mockFetch.mockResolvedValue(jsonResponse([friendTags]));

    await fetchRelationshipTags({ userId: "friend-1" });

    expect(mockFetch.mock.calls[0][0]).toBe(
      "/api/v1/analytics/tags/?user_id=friend-1",
    );
  });
});

describe("helpers", () => {
  it("indexes tags by friend", () => {
    expect(tagsByFriend([friendTags])).toEqual({
      "friend-1": friendTags.tags,
    });
  });

  it("formats win rates", () => {
    expect(formatWinRate(66.7)).toBe("66.7%");
    expect(formatWinRate(null)).toBe("N/A");
  });

  it("formats play time", () => {
    expect(formatPlayTime(45)).toBe("45m");
    expect(formatPlayTime(120)).toBe("2h");
    expect(formatPlayTime(135)).toBe("2h 15m");
  });

  it("formats play dates without shifting the day", () => {
    expect(formatPlayDate("2026-11-20")).toContain("20");
    expect(formatPlayDate("2026-11-20")).toContain("2026");
  });
});
