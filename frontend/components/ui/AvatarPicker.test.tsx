import { fireEvent, render, screen } from "@testing-library/react";
import AvatarPicker from "./AvatarPicker";

describe("AvatarPicker", () => {
  it("renders the available avatars", () => {
    render(
      <AvatarPicker
        selected=""
        onSelect={jest.fn()}
      />
    );

    const avatars = screen.getAllByAltText("avatar");

    expect(avatars).toHaveLength(9);
  });

  it("calls onSelect when an avatar is clicked", () => {
    const onSelect = jest.fn();

    render(
      <AvatarPicker
        selected=""
        onSelect={onSelect}
      />
    );

    const avatars = screen.getAllByAltText("avatar");

    fireEvent.click(avatars[0]);

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("/avatars/avatar1.webp");
  });
});