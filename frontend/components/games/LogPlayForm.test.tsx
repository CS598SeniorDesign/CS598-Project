import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import LogPlayForm from "./LogPlayForm";

const mockFetch = jest.fn();

const ME_ID = "550e8400-e29b-41d4-a716-446655440000";
const ALEX_ID = "550e8400-e29b-41d4-a716-446655440001";
const SAM_ID = "550e8400-e29b-41d4-a716-446655440002";

const currentUser = { user_id: ME_ID, display_name: "Jordan" };

const friends = [
  { user_id: ALEX_ID, display_name: "Alex" },
  { user_id: SAM_ID, display_name: "Sam" },
];

const defaultProps = {
  gameId: 13,
  gameName: "Catan",
  onClose: jest.fn(),
};

type MockResponse = { ok: boolean; status: number; json?: () => unknown };

function respond(status: number, body?: unknown): Promise<MockResponse> {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

/**
 * Route the form's requests: the logged-in user's profile, their friends, the player search and the play POST.
 * Pass a status to make one endpoint fail.
 */
function mockApi({
  profileStatus = 200,
  friendsStatus = 200,
  playStatus = 201,
}: {
  profileStatus?: number;
  friendsStatus?: number;
  playStatus?: number;
} = {}) {
  mockFetch.mockImplementation((url: string) => {
    if (url === "/api/v1/profile/") return respond(profileStatus, currentUser);
    if (url === "/api/v1/friends/") return respond(friendsStatus, friends);
    if (url.startsWith("/api/v1/players/")) return respond(200, friends);
    return respond(playStatus);
  });
}

/** Render the form and wait until it has loaded the logged-in user. */
async function renderForm() {
  const result = render(<LogPlayForm {...defaultProps} />);

  await waitFor(() => {
    expect(
      screen.queryByText("Loading your QuestLog account..."),
    ).not.toBeInTheDocument();
  });

  return result;
}

function addPlayer() {
  fireEvent.click(screen.getByRole("button", { name: /add another player/i }));
}

function setPlayerType(index: number, type: "guest" | "registered") {
  fireEvent.change(screen.getAllByLabelText("Player Type")[index], {
    target: { value: type },
  });
}

function playRequests() {
  return mockFetch.mock.calls.filter(([url]) => url === "/api/v1/plays/");
}

function getPlayRequest() {
  const request = playRequests()[0];

  if (!request) {
    throw new Error("Expected a play session POST request.");
  }

  return {
    url: request[0] as string,
    options: request[1] as RequestInit,
    payload: JSON.parse(request[1].body as string),
  };
}

async function chooseFriend(index: number, userId: string) {
  const name = userId === ALEX_ID ? "Alex" : "Sam";

  await waitFor(() => {
    const selectors = screen.getAllByLabelText("Select Registered User");

    expect(
      within(selectors[index] as HTMLElement).getByRole("option", { name }),
    ).toBeInTheDocument();
  });

  fireEvent.change(screen.getAllByLabelText("Select Registered User")[index], {
    target: { value: userId },
  });
}

describe("LogPlayForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();

    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      writable: true,
      value: mockFetch,
    });

    mockApi();
  });

  it("renders the form with the selected game name", async () => {
    await renderForm();

    expect(
      screen.getByRole("heading", { name: "Log a Play" }),
    ).toBeInTheDocument();

    expect(screen.getByText("Catan")).toBeInTheDocument();

    expect(screen.getByRole("button", { name: "Save Play" })).toBeEnabled();
  });

  it("adds the logged-in user as the first player", async () => {
    await renderForm();

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/profile/",
      expect.objectContaining({ method: "GET" }),
    );

    expect(screen.getAllByLabelText("Player Type")[0]).toHaveValue(
      "registered",
    );

    expect(screen.getByText("Selected: Jordan")).toBeInTheDocument();
  });

  it("disables saving when the user's profile cannot be loaded", async () => {
    mockApi({ profileStatus: 401 });

    await renderForm();

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Please log in to record your plays.",
    );

    expect(screen.getByRole("button", { name: "Save Play" })).toBeDisabled();
  });

  it("allows users to add another player", async () => {
    await renderForm();

    expect(screen.getAllByLabelText("Player Type")).toHaveLength(1);

    addPlayer();

    expect(screen.getAllByLabelText("Player Type")).toHaveLength(2);
    expect(screen.getAllByPlaceholderText("Enter player name")).toHaveLength(1);
  });

  it("allows users to remove a player", async () => {
    await renderForm();
    addPlayer();

    expect(screen.getAllByLabelText("Player Type")).toHaveLength(2);

    fireEvent.click(screen.getAllByRole("button", { name: "Remove" })[1]);

    expect(screen.getAllByLabelText("Player Type")).toHaveLength(1);
  });

  it("closes the form when the close button is clicked", async () => {
    await renderForm();

    fireEvent.click(screen.getByRole("button", { name: "Close Log Play" }));

    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("rejects duplicate guest names", async () => {
    await renderForm();

    addPlayer();
    addPlayer();

    const nameInputs = screen.getAllByPlaceholderText("Enter player name");
    fireEvent.change(nameInputs[0], { target: { value: "Alex" } });
    fireEvent.change(nameInputs[1], { target: { value: "alex" } });

    fireEvent.click(screen.getByRole("button", { name: "Save Play" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Each guest player must have a different name.",
    );

    expect(playRequests()).toHaveLength(0);
  });

  it("submits a play session with players and scores", async () => {
    await renderForm();

    addPlayer();
    fireEvent.change(screen.getByPlaceholderText("Enter player name"), {
      target: { value: "Sam" },
    });

    const scoreInputs = screen.getAllByPlaceholderText("Score");
    fireEvent.change(scoreInputs[0], { target: { value: "10" } });
    fireEvent.change(scoreInputs[1], { target: { value: "8" } });

    fireEvent.click(screen.getAllByRole("checkbox")[0]);

    fireEvent.change(screen.getByPlaceholderText("How was game night?"), {
      target: { value: "Testing QuestLog" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save Play" }));

    expect(
      await screen.findByText("Your play session was saved successfully!"),
    ).toBeInTheDocument();

    const { options, payload } = getPlayRequest();

    expect(playRequests()).toHaveLength(1);
    expect(options.method).toBe("POST");
    expect(options.credentials).toBe("same-origin");

    expect(payload.game).toBe(13);
    expect(payload.quantity).toBe(1);
    expect(payload.is_incomplete).toBe(false);
    expect(payload.notes).toBe("Testing QuestLog");

    expect(payload.players).toEqual([
      { user_id: ME_ID, score: 10, is_winner: true },
      { guest_name: "Sam", score: 8, is_winner: false },
    ]);
  });

  it("displays an error when the API rejects the request", async () => {
    mockApi({ playStatus: 400 });
    await renderForm();

    fireEvent.click(screen.getByRole("button", { name: "Save Play" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to save this play.",
    );
  });

  it("displays a login error for unauthorized requests", async () => {
    mockApi({ playStatus: 401 });
    await renderForm();

    fireEvent.click(screen.getByRole("button", { name: "Save Play" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Please log in again.",
    );
  });

  it("loads friends for registered players", async () => {
    await renderForm();

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/friends/",
        expect.objectContaining({ credentials: "same-origin" }),
      );
    });

    const selector = screen.getByLabelText("Select Registered User");

    expect(
      await within(selector).findByRole("option", { name: "Alex" }),
    ).toBeInTheDocument();

    expect(
      within(selector).getByRole("option", { name: "Sam" }),
    ).toBeInTheDocument();
  });

  it("searches registered users by display name", async () => {
    await renderForm();

    fireEvent.click(screen.getByRole("button", { name: "Search Users" }));

    fireEvent.change(
      screen.getByPlaceholderText("Enter at least 2 characters"),
      { target: { value: "al" } },
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/players/?search=al",
        expect.objectContaining({ credentials: "same-origin" }),
      );
    });

    expect(
      await screen.findByRole("option", { name: "Alex" }),
    ).toBeInTheDocument();
  });

  it("submits registered players using user_id", async () => {
    await renderForm();

    addPlayer();
    setPlayerType(1, "registered");
    await chooseFriend(1, ALEX_ID);

    fireEvent.click(screen.getByRole("button", { name: "Save Play" }));

    await waitFor(() => {
      expect(getPlayRequest().payload.players).toEqual([
        { user_id: ME_ID, is_winner: false },
        { user_id: ALEX_ID, is_winner: false },
      ]);
    });

    expect(
      await screen.findByText("Your play session was saved successfully!"),
    ).toBeInTheDocument();
  });

  it("supports guest and registered players in one session", async () => {
    await renderForm();

    setPlayerType(0, "guest");
    fireEvent.change(screen.getByPlaceholderText("Enter player name"), {
      target: { value: "Guest Taylor" },
    });

    addPlayer();
    setPlayerType(1, "registered");
    await chooseFriend(0, SAM_ID);

    fireEvent.click(screen.getByRole("button", { name: "Save Play" }));

    await waitFor(() => {
      expect(getPlayRequest().payload.players).toEqual([
        { guest_name: "Guest Taylor", is_winner: false },
        { user_id: SAM_ID, is_winner: false },
      ]);
    });

    expect(
      await screen.findByText("Your play session was saved successfully!"),
    ).toBeInTheDocument();
  });

  it("prevents adding the same registered user twice", async () => {
    await renderForm();

    await chooseFriend(0, ALEX_ID);

    addPlayer();
    setPlayerType(1, "registered");

    await waitFor(() => {
      const selectors = screen.getAllByLabelText("Select Registered User");

      expect(
        within(selectors[1] as HTMLElement).getByRole("option", {
          name: "Sam",
        }),
      ).toBeInTheDocument();
    });

    const secondSelector = screen.getAllByLabelText(
      "Select Registered User",
    )[1] as HTMLElement;

    expect(
      within(secondSelector).queryByRole("option", { name: "Alex" }),
    ).not.toBeInTheDocument();
  });

  it("displays an error when friends cannot be loaded", async () => {
    mockApi({ friendsStatus: 500 });
    await renderForm();

    expect(
      await screen.findByText(
        "Unable to load registered players. Please try again.",
      ),
    ).toBeInTheDocument();
  });
});
