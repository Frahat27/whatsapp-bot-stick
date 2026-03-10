"use client";

import { use } from "react";
import { ConversationList } from "@/components/conversations/ConversationList";
import { ChatView } from "@/components/chat/ChatView";

export default function ConversationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const conversationId = parseInt(id, 10);

  return (
    <div className="flex h-full w-full">
      {/* Sidebar — hidden on mobile, visible on desktop */}
      <div className="hidden md:block w-[380px] flex-shrink-0 bg-white dark:bg-[var(--card)] border-r border-[#e9edef] dark:border-[var(--border)]">
        <ConversationList activeId={conversationId} />
      </div>
      {/* Chat — full width on mobile */}
      <div className="flex-1 w-full">
        <ChatView conversationId={conversationId} />
      </div>
    </div>
  );
}
