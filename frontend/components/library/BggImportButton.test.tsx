import "@testing-library/jest-dom";
import { act, fireEvent, render, screen } from "@testing-library/react";
import BggImportButton, { SYNC_POLL_INTERVAL } from "./BggImportButton";
import {
  fetchBggCollectionSyncStatus,
  startBggCollectionSync,
} from "@/lib/library";

jest.mock("@/lib/library", () => ({
  ...jest.requireActual("@/lib/library"),
  startBggCollectionSync: jest.fn(),
  fetchBggCollectionSyncStatus: jest.fn(),
}));

const mockStart = startBggCollectionSync as jest.Mock;
const mockStatus = fetchBggCollectionSyncStatus as jest.Mock;

const TASK_ID = "550e8400-e29b-41d4-a716-446655440000";

beforeEach(() => {
  jest.useFakeTimers();
  mockStart.mockReset();
  mockStatus.mockReset();
});

afterEach(() => {
  jest.useRealTimers();
});

async function advance() {
  await act(async () => {
    jest.advanceTimersByTime(SYNC_POLL_INTERVAL);
  });
}

describe("BggImportButton", () => {
  it("polls until the import finishes, then reloads the library", async () => {
    const onImported = jest.fn();
    mockStart.mockResolvedValue({
      task_id: TASK_ID,
      status: "queued",
      detail: "Your BoardGameGeek collection is being imported.",
    });
    mockStatus
      .mockResolvedValueOnce({
        task_id: TASK_ID,
        status: "running",
        detail: "Importing",
      })
      .mockResolvedValueOnce({
        task_id: TASK_ID,
        status: "succeeded",
        detail: "Done",
        added: 4,
        updated: 1,
        skipped: 2,
      });

    render(<BggImportButton onImported={onImported} />);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Import from BGG" }));
    });

    expect(screen.getByRole("button", { name: "Importing..." })).toBeDisabled();
    await advance();
    expect(onImported).not.toHaveBeenCalled();
    await advance();

    expect(mockStatus).toHaveBeenCalledTimes(2);
    expect(onImported).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Import finished: 4 added, 1 updated, 2 skipped.",
    );
    expect(
      screen.getByRole("button", { name: "Import from BGG" }),
    ).toBeEnabled();
  });

  it("links to the profile when no BGG username is set", async () => {
    mockStart.mockRejectedValue(
      new Error(
        "Link a BoardGameGeek username to your profile before importing your collection.",
      ),
    );

    render(<BggImportButton onImported={jest.fn()} />);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Import from BGG" }));
    });

    expect(
      screen.getByRole("link", { name: "Add your BGG username" }),
    ).toHaveAttribute("href", "/profile/edit");
  });

  it("reports a failed import without reloading", async () => {
    const onImported = jest.fn();
    mockStart.mockResolvedValue({
      task_id: TASK_ID,
      status: "queued",
      detail: "",
    });
    mockStatus.mockResolvedValue({
      task_id: TASK_ID,
      status: "failed",
      detail:
        "BoardGameGeek could not find a collection for your linked username.",
    });

    render(<BggImportButton onImported={onImported} />);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Import from BGG" }));
    });
    await advance();

    expect(onImported).not.toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent(
      "could not find a collection",
    );
  });
});
