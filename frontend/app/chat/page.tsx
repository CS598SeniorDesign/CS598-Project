import { Suspense } from "react";
import ChatWorkspace from "@/components/chat/ChatWorkspace";

export default function ChatPage() {
  return (
    <Suspense
      fallback={<p className="p-8 text-muted">Loading Weeple Chat...</p>}
    >
      <ChatWorkspace />
    </Suspense>
  );
}
