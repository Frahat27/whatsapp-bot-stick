"use client";

import { use, useState } from "react";
import { ConversationList } from "@/components/conversations/ConversationList";
import { ChatView } from "@/components/chat/ChatView";
import { PatientSidebar } from "@/components/sidebar/PatientSidebar";
import { ConversationDetail } from "@/lib/types";

export default function ConversationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const conversationId = parseInt(id, 10);
  const [showSidebar, setShowSidebar] = useState(true);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);

  return (
    <div className="flex h-full w-full">
      {/* Conversation list — hidden on mobile */}
      <div className="hidden md:block w-[380px] flex-shrink-0 bg-white dark:bg-[var(--card)] border-r border-[#e9edef] dark:border-[var(--border)]">
        <ConversationList activeId={conversationId} />
      </div>
      {/* Chat — flex grows */}
      <div className="flex-1 w-full min-w-0">
        <ChatView
          conversationId={conversationId}
          onToggleSidebar={() => setShowSidebar((s) => !s)}
          showSidebar={showSidebar}
          onDetailLoaded={setDetail}
        />
      </div>
      {/* Patient sidebar — hidden on small screens, toggleable on lg+ */}
      {showSidebar && (
        <div className="hidden lg:block w-[320px] flex-shrink-0 border-l border-[#e9edef] dark:border-[var(--border)] animate-page-enter">
          <PatientSidebar
            detail={detail}
            onDetailUpdate={setDetail}
          />
        </div>
      )}
    </div>
  );
}
