"use client";

import { useEffect, useState } from "react";
import {
  fetchRelationshipTags,
  tagsByFriend,
  type RelationshipTag,
} from "@/lib/analytics";

/**
 * The signed-in user's relationship tags keyed by friend user ID, loaded once.
 * Pass a user ID to load only that friend's tags. Tags are extra context, so
 * if they fail to load, friends are simply shown untagged.
 */
export function useRelationshipTags(userId?: string) {
  const [tags, setTags] = useState<Record<string, RelationshipTag[]>>({});

  useEffect(() => {
    const controller = new AbortController();

    fetchRelationshipTags({ userId, signal: controller.signal })
      .then((entries) => {
        if (!controller.signal.aborted) setTags(tagsByFriend(entries));
      })
      .catch(() => undefined);

    return () => controller.abort();
  }, [userId]);

  return tags;
}
