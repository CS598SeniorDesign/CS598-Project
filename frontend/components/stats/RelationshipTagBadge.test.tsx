import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import {
  RelationshipTagBadge,
  RelationshipTagList,
} from "./RelationshipTagBadge";
import {
  RELATIONSHIP_TAG_TYPES,
  type RelationshipTag,
  type RelationshipTagType,
} from "@/lib/analytics";

function makeTag(tagType: RelationshipTagType, name: string): RelationshipTag {
  return {
    tag_type: tagType,
    name,
    description: `${name} description.`,
    assigned_at: "2026-11-20T10:00:00Z",
  };
}

describe("RelationshipTagBadge", () => {
  it("shows the tag's name and explains it on hover", () => {
    render(
      <RelationshipTagBadge tag={makeTag("MORTAL_ENEMY", "Mortal Enemy")} />,
    );

    const badge = screen.getByLabelText(
      "Mortal Enemy: Mortal Enemy description.",
    );
    expect(badge).toHaveTextContent("Mortal Enemy");
    expect(badge).toHaveAttribute("title", "Mortal Enemy description.");
  });

  it("has a style for every tag type", () => {
    for (const tagType of RELATIONSHIP_TAG_TYPES) {
      const { unmount } = render(
        <RelationshipTagBadge tag={makeTag(tagType, tagType)} compact />,
      );

      expect(screen.getByText(tagType).className).toContain(
        "[html[data-theme=light]_&]:text-",
      );
      unmount();
    }
  });
});

describe("RelationshipTagList", () => {
  it("shows a badge for each tag", () => {
    render(
      <RelationshipTagList
        tags={[makeTag("RIVAL", "Rival"), makeTag("REGULAR", "Regular")]}
      />,
    );

    expect(screen.getByText("Rival")).toBeInTheDocument();
    expect(screen.getByText("Regular")).toBeInTheDocument();
  });

  it("renders nothing for a friend without tags", () => {
    const { container } = render(<RelationshipTagList />);

    expect(container).toBeEmptyDOMElement();
  });
});
