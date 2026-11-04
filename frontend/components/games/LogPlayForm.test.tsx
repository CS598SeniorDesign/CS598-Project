import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import LogPlayForm from "./LogPlayForm";

const mockFetch = jest.fn();

const ALEX_ID = "550e8400-e29b-41d4-a716-446655440001";
const SAM_ID = "550e8400-e29b-41d4-a716-446655440002";

const friends = [
  { user_id: ALEX_ID, display_name: "Alex" },
  { user_id: SAM_ID, display_name: "Sam" },
];

const defaultProps = {
  gameId: 13,
  gameName: "Catan",
  onClose: jest.fn(),
};

function renderForm() {
  return render(<LogPlayForm {...defaultProps} />);
}

function addSecondPlayer() {
  fireEvent.click(screen.getByRole("button", { name: /add another player/i }));
}

function fillPlayerNames(firstName: string, secondName: string) {
  const nameInputs = screen.getAllByPlaceholderText("Enter player name");

  fireEvent.change(nameInputs[0], {
    target: { value: firstName },
  });

  fireEvent.change(nameInputs[1], {
    target: { value: secondName },
  });
}

function mockSuccessfulRequests() {
  mockFetch.mockImplementation((url: string) => {
    if (url === "/api/v1/friends/") {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => friends,
      });
    }

    if (url.startsWith("/api/v1/players/")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => friends,
      });
    }

    return Promise.resolve({
      ok: true,
      status: 201,
    });
  });
}

function getPlayRequest() {
  const request = mockFetch.mock.calls.find(
    ([url]) => url === "/api/v1/plays/",
  );

  if (!request) {
    throw new Error("Expected a play session POST request.");
  }

  return {
    url: request[0] as string,
    options: request[1] as RequestInit,
    payload: JSON.parse(request[1].body as string),
  };
}

function selectRegisteredPlayer(index: number) {
  const typeSelectors = screen.getAllByLabelText("Player Type");

  fireEvent.change(typeSelectors[index], {
    target: { value: "registered" },
  });
}

async function chooseFriend(index: number, userId: string) {
  const selectors = await screen.findAllByLabelText("Select Registered User");

  await waitFor(() => {
    expect(
      within(selectors[index] as HTMLElement).getByRole("option", {
        name: userId === ALEX_ID ? "Alex" : "Sam",
      }),
    ).toBeInTheDocument();
  });

  fireEvent.change(selectors[index], {
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

    mockFetch.mockResolvedValue({
      ok: true,
      status: 201,
    });
  });

  // Original tests

  it("renders the form with the selected game name", () => {
    renderForm();

    expect(
      screen.getByRole("heading", { name: "Log a Play" }),
    ).toBeInTheDocument();

    expect(screen.getByText("Catan")).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: "Save Play" }),
    ).toBeInTheDocument();
  });

  it("allows users to add another player", () => {
    renderForm();

    expect(screen.getAllByPlaceholderText("Enter player name")).toHaveLength(1);

    addSecondPlayer();

    expect(screen.getAllByPlaceholderText("Enter player name")).toHaveLength(2);
  });

  it("allows users to remove a player", () => {
    renderForm();
    addSecondPlayer();

    expect(screen.getAllByPlaceholderText("Enter player name")).toHaveLength(2);

    const removeButtons = screen.getAllByRole("button", {
      name: "Remove",
    });

    fireEvent.click(removeButtons[1]);

    expect(screen.getAllByPlaceholderText("Enter player name")).toHaveLength(1);
  });

  it("closes the form when the close button is clicked", () => {
    renderForm();

    fireEvent.click(screen.getByRole("button", { name: "Close Log Play" }));

    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("rejects duplicate player names", () => {
    renderForm();

    addSecondPlayer();
    fillPlayerNames("Alex", "alex");

    fireEvent.click(screen.getByRole("button", { name: "Save Play" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Each guest player must have a different name.",
    );

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("submits a play session with players and scores", async () => {
    renderForm();

    addSecondPlayer();
    fillPlayerNames("Alex", "Sam");

    const scoreInputs = screen.getAllByPlaceholderText("Score");

    fireEvent.change(scoreInputs[0], {
      target: { value: "10" },
    });

    fireEvent.change(scoreInputs[1], {
      target: { value: "8" },
    });

    const winnerCheckboxes = screen.getAllByRole("checkbox");
    fireEvent.click(winnerCheckboxes[0]);

    fireEvent.change(screen.getByPlaceholderText("How was game night?"), {
      target: { value: "Testing QuestLog" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save Play" }));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    const { url, options, payload } = getPlayRequest();

    expect(url).toBe("/api/v1/plays/");
    expect(options.method).toBe("POST");
    expect(options.credentials).toBe("same-origin");

    expect(payload.game).toBe(13);
    expect(payload.quantity).toBe(1);
    expect(payload.is_incomplete).toBe(false);
    expect(payload.notes).toBe("Testing QuestLog");

    expect(payload.players).toEqual([
      {
        guest_name: "Alex",
        score: 10,
        is_winner: true,
      },
      {
        guest_name: "Sam",
        score: 8,
        is_winner: false,
      },
    ]);

    expect(
      await screen.findByText("Your play session was saved successfully!"),
    ).toBeInTheDocument();
  });

  it("displays an error when the API rejects the request", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 400,
    });

    renderForm();

    fireEvent.change(screen.getByPlaceholderText("Enter player name"), {
      target: { value: "Alex" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save Play" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to save this play.",
    );
  });

  it("displays a login error for unauthorized requests", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
    });

    renderForm();

    fireEvent.change(screen.getByPlaceholderText("Enter player name"), {
      target: { value: "Alex" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save Play" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Please log in again.",
    );
  });

  // New registered-player tests

  it("loads friends when registered player is selected", async () => {
    mockSuccessfulRequests();
    renderForm();

    selectRegisteredPlayer(0);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/friends/",
        expect.objectContaining({
          credentials: "same-origin",
        }),
      );
    });

    const selector = await screen.findByLabelText("Select Registered User");

    expect(
      await within(selector).findByRole("option", {
        name: "Alex",
      }),
    ).toBeInTheDocument();

    expect(
      within(selector).getByRole("option", {
        name: "Sam",
      }),
    ).toBeInTheDocument();
  });

  it("searches registered users by display name", async () => {
    mockSuccessfulRequests();
    renderForm();

    selectRegisteredPlayer(0);

    fireEvent.click(screen.getByRole("button", { name: "Search Users" }));

    fireEvent.change(
      screen.getByPlaceholderText("Enter at least 2 characters"),
      {
        target: { value: "al" },
      },
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/players/?search=al",
        expect.objectContaining({
          credentials: "same-origin",
        }),
      );
    });

    expect(
      await screen.findByRole("option", { name: "Alex" }),
    ).toBeInTheDocument();
  });

  it("submits a registered player using user_id", async () => {
    mockSuccessfulRequests();
    renderForm();

    selectRegisteredPlayer(0);
    await chooseFriend(0, ALEX_ID);

    fireEvent.click(screen.getByRole("button", { name: "Save Play" }));

    await waitFor(() => {
      expect(getPlayRequest().payload.players).toEqual([
        {
          user_id: ALEX_ID,
          is_winner: false,
        },
      ]);
    });
  });

  it("supports guest and registered players in one session", async () => {
    mockSuccessfulRequests();
    renderForm();

    fireEvent.change(screen.getByPlaceholderText("Enter player name"), {
      target: { value: "Guest Taylor" },
    });

    addSecondPlayer();
    selectRegisteredPlayer(1);
    await chooseFriend(0, SAM_ID);

    fireEvent.click(screen.getByRole("button", { name: "Save Play" }));

    await waitFor(() => {
      expect(getPlayRequest().payload.players).toEqual([
        {
          guest_name: "Guest Taylor",
          is_winner: false,
        },
        {
          user_id: SAM_ID,
          is_winner: false,
        },
      ]);
    });
  });

  it("prevents adding the same registered user twice", async () => {
    mockSuccessfulRequests();
    renderForm();

    selectRegisteredPlayer(0);
    await chooseFriend(0, ALEX_ID);

    addSecondPlayer();
    selectRegisteredPlayer(1);

    const selectors = await screen.findAllByLabelText("Select Registered User");

    await waitFor(() => {
      expect(
        within(selectors[1] as HTMLElement).getByRole("option", {
          name: "Sam",
        }),
      ).toBeInTheDocument();
    });

    expect(
      within(selectors[1] as HTMLElement).queryByRole("option", {
        name: "Alex",
      }),
    ).not.toBeInTheDocument();
  });

  it("displays an error when friends cannot be loaded", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
    });

    renderForm();
    selectRegisteredPlayer(0);

    expect(
      await screen.findByText(
        "Unable to load registered players. Please try again.",
      ),
    ).toBeInTheDocument();
  });
});
