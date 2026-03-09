"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { adminWs } from "@/lib/ws";
import { MessageData, WsEvent, ConversationDetail } from "@/lib/types";
import { ToolCallCard } from "./ToolCallCard";

const contactTypeLabels: Record<string, { text: string; color: string }> = {
  paciente: { text: "Paciente", color: "bg-[#364c85]/10 text-[#364c85]" },
  lead: { text: "Lead", color: "bg-[#95b2ee]/20 text-[#364c85]" },
  nuevo: { text: "Nuevo", color: "bg-[#e7f1ac]/60 text-[#2a3a1e]" },
  admin: { text: "Admin", color: "bg-orange-100 text-orange-700" },
};

function getInitials(name: string | null, phone: string): string {
  if (name) {
    const parts = name.split(/[,\s]+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.substring(0, 2).toUpperCase();
  }
  return phone.slice(-2);
}

/* Double-check icon (WhatsApp style) */
function DoubleCheck({ className = "" }: { className?: string }) {
  return (
    <svg width="16" height="11" viewBox="0 0 16 11" className={className}>
      <path
        d="M11.071.653a.457.457 0 0 0-.304-.102.493.493 0 0 0-.381.178l-6.19 7.636-2.011-2.085a.5.5 0 0 0-.381-.178.456.456 0 0 0-.304.102.493.493 0 0 0-.178.381c0 .152.076.304.178.381l2.239 2.316a.57.57 0 0 0 .406.178c.152 0 .33-.076.406-.178L11.071 1.4a.52.52 0 0 0 .178-.381.457.457 0 0 0-.178-.366z"
        fill="currentColor"
      />
      <path
        d="M14.613.653a.457.457 0 0 0-.304-.102.493.493 0 0 0-.381.178l-6.19 7.636-1.006-1.043.787-.787-1.016-1.054-1.467 1.467 1.449 1.5a.57.57 0 0 0 .406.178c.152 0 .33-.076.406-.178L14.613 1.4a.52.52 0 0 0 .178-.381.457.457 0 0 0-.178-.366z"
        fill="currentColor"
      />
    </svg>
  );
}

/* Single check icon */
function SingleCheck({ className = "" }: { className?: string }) {
  return (
    <svg width="12" height="11" viewBox="0 0 12 11" className={className}>
      <path
        d="M11.071.653a.457.457 0 0 0-.304-.102.493.493 0 0 0-.381.178l-6.19 7.636-2.011-2.085a.5.5 0 0 0-.381-.178.456.456 0 0 0-.304.102.493.493 0 0 0-.178.381c0 .152.076.304.178.381l2.239 2.316a.57.57 0 0 0 .406.178c.152 0 .33-.076.406-.178L11.071 1.4a.52.52 0 0 0 .178-.381.457.457 0 0 0-.178-.366z"
        fill="currentColor"
      />
    </svg>
  );
}

/* Skeleton loader for messages */
function MessagesSkeleton() {
  return (
    <div className="max-w-3xl mx-auto space-y-4 py-4">
      <div className="flex justify-start">
        <div className="w-[55%] space-y-2 rounded-2xl bg-white p-4 shadow-sm">
          <div className="skeleton-stick h-3 w-3/4 rounded-full" />
          <div className="skeleton-stick h-3 w-1/2 rounded-full" />
        </div>
      </div>
      <div className="flex justify-end">
        <div className="w-[45%] space-y-2 rounded-2xl bg-[#e7f1ac]/40 p-4 shadow-sm">
          <div className="skeleton-stick h-3 w-full rounded-full" />
          <div className="skeleton-stick h-3 w-2/3 rounded-full" />
        </div>
      </div>
      <div className="flex justify-start">
        <div className="w-[60%] space-y-2 rounded-2xl bg-white p-4 shadow-sm">
          <div className="skeleton-stick h-3 w-full rounded-full" />
          <div className="skeleton-stick h-3 w-5/6 rounded-full" />
          <div className="skeleton-stick h-3 w-1/3 rounded-full" />
        </div>
      </div>
      <div className="flex justify-end">
        <div className="w-[40%] space-y-2 rounded-2xl bg-[#e7f1ac]/40 p-4 shadow-sm">
          <div className="skeleton-stick h-3 w-full rounded-full" />
        </div>
      </div>
    </div>
  );
}

export function ChatView({ conversationId }: { conversationId: number }) {
  const [messages, setMessages] = useState<MessageData[]>([]);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [simPhone, setSimPhone] = useState("");
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const [newMsgCount, setNewMsgCount] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior,
      });
      setNewMsgCount(0);
    }
  }, []);

  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    setShowScrollBtn(distanceFromBottom > 200);
    if (distanceFromBottom <= 200) setNewMsgCount(0);
  }, []);

  // Fetch messages and conversation detail
  useEffect(() => {
    setLoading(true);
    const fetchData = async () => {
      try {
        const [msgRes, detRes] = await Promise.all([
          api.getMessages(conversationId),
          api.getConversation(conversationId),
        ]);
        if (msgRes.ok) setMessages(await msgRes.json());
        if (detRes.ok) {
          const d = await detRes.json();
          setDetail(d);
          setSimPhone(d.phone);
        }
      } catch (e) {
        console.error("Failed to fetch chat data:", e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [conversationId]);

  // Real-time message updates
  useEffect(() => {
    const unsub = adminWs.on("new_message", (event: WsEvent) => {
      if (event.conversation_id === conversationId && event.message) {
        setMessages((prev) => {
          if (prev.some((m) => m.id === event.message!.id)) return prev;
          return [
            ...prev,
            {
              id: event.message!.id,
              role: event.message!.role as "user" | "assistant",
              content: event.message!.content,
              message_type: "text",
              created_at: event.message!.created_at,
              tool_calls: [],
            },
          ];
        });
        // If scrolled up, increment counter
        if (scrollRef.current) {
          const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
          if (scrollHeight - scrollTop - clientHeight > 200) {
            setNewMsgCount((c) => c + 1);
          }
        }
      }
    });
    return unsub;
  }, [conversationId]);

  // Auto-scroll on new messages
  useEffect(() => {
    scrollToBottom("instant");
  }, [messages, scrollToBottom]);

  // Send simulated message
  const handleSend = async () => {
    if (!inputText.trim() || !simPhone.trim()) return;
    setSending(true);
    try {
      const res = await api.simulate(simPhone, inputText);
      if (res.ok) {
        const msgRes = await api.getMessages(conversationId);
        if (msgRes.ok) setMessages(await msgRes.json());
      }
      setInputText("");
      inputRef.current?.focus();
    } catch (e) {
      console.error("Simulate failed:", e);
    } finally {
      setSending(false);
    }
  };

  // Takeover toggle
  const handleTakeover = async () => {
    if (!detail) return;
    const newStatus = detail.status === "admin_takeover" ? "bot_active" : "admin_takeover";
    try {
      await api.updateState(conversationId, { status: newStatus });
      setDetail({ ...detail, status: newStatus });
    } catch (e) {
      console.error("Takeover toggle failed:", e);
    }
  };

  const ct = detail?.contact_type ? contactTypeLabels[detail.contact_type] : null;
  const isTakeover = detail?.status === "admin_takeover";

  return (
    <div className="flex flex-col h-full bg-[#f0f2f5] dark:bg-[var(--chat-panel-bg)] animate-page-enter">
      {/* ── Chat Header ────────────────────────────────── */}
      <div className="flex items-center justify-between px-5 py-3 bg-white dark:bg-[var(--card)] border-b border-[#e9edef] dark:border-[var(--border)]">
        <div className="flex items-center gap-3">
          {/* Avatar */}
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#364c85] to-[#5a7bc4] flex items-center justify-center flex-shrink-0 shadow-sm">
            <span className="text-white font-semibold text-sm">
              {getInitials(detail?.patient_name || null, detail?.phone || "")}
            </span>
          </div>
          {/* Info */}
          <div>
            <h2 className="font-semibold text-[#111b21] dark:text-[var(--foreground)] text-[15px]">
              {detail?.patient_name || detail?.phone || "Cargando..."}
            </h2>
            <div className="flex items-center gap-2 text-xs text-[#667781] dark:text-[var(--muted-foreground)]">
              <span className="tabular-nums">{detail?.phone}</span>
              {ct && (
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${ct.color}`}>
                  {ct.text}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2.5">
          {/* Status badge */}
          <span className={`text-xs px-3 py-1.5 rounded-full font-medium transition-all duration-300 ${
            isTakeover
              ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300"
              : "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
          }`}>
            <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${isTakeover ? "bg-orange-500" : "bg-emerald-500"}`} />
            {isTakeover ? "Admin takeover" : "Sofia activa"}
          </span>
          {/* Takeover button */}
          <button
            onClick={handleTakeover}
            className={`p-2.5 rounded-xl transition-all duration-200 ${
              isTakeover
                ? "bg-emerald-50 text-emerald-600 hover:bg-emerald-100 dark:bg-emerald-900/20 dark:hover:bg-emerald-900/30"
                : "bg-[#f0f2f5] text-[#667781] hover:bg-[#e9edef] dark:bg-[var(--muted)] dark:hover:bg-[var(--border)]"
            }`}
            title={isTakeover ? "Devolver a Sofia" : "Tomar control"}
          >
            {isTakeover ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="10" rx="2" />
                <circle cx="12" cy="5" r="2" />
                <path d="M12 7v4" />
                <line x1="8" y1="16" x2="8" y2="16" />
                <line x1="16" y1="16" x2="16" y2="16" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* ── Messages Area ─────────────────────────────── */}
      <div
        className="flex-1 overflow-y-auto wa-scrollbar chat-bg-pattern px-4 py-3 relative"
        ref={scrollRef}
        onScroll={handleScroll}
      >
        {loading ? (
          <MessagesSkeleton />
        ) : (
          <div className="max-w-3xl mx-auto space-y-1">
            {messages.map((msg, idx) => {
              const showDate = idx === 0 || (
                new Date(msg.created_at).toDateString() !==
                new Date(messages[idx - 1].created_at).toDateString()
              );
              const isUser = msg.role === "user";
              const animClass = isUser ? "animate-msg-in-right" : "animate-msg-in-left";

              return (
                <div key={msg.id}>
                  {/* Date separator — pill style with blur */}
                  {showDate && (
                    <div className="flex justify-center my-4 animate-msg-fade">
                      <span className="date-pill text-[11px] text-[#667781] px-4 py-1.5 rounded-full font-medium">
                        {new Date(msg.created_at).toLocaleDateString("es-AR", {
                          weekday: "long",
                          day: "numeric",
                          month: "long",
                        })}
                      </span>
                    </div>
                  )}

                  {/* Tool calls */}
                  {msg.role === "assistant" && msg.tool_calls.length > 0 && (
                    <div className="space-y-1.5 mb-1.5 animate-msg-fade">
                      {msg.tool_calls.map((tc) => (
                        <ToolCallCard key={tc.id} toolCall={tc} />
                      ))}
                    </div>
                  )}

                  {/* Message bubble */}
                  {msg.content && (
                    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-0.5 ${animClass}`}>
                      <div
                        className={`group relative max-w-[65%] rounded-2xl px-3 py-2 ${
                          isUser
                            ? "bg-[var(--bubble-outgoing)] rounded-tr-sm bubble-tail-right shadow-sm shadow-[#e7f1ac]/30"
                            : "bg-[var(--bubble-incoming)] rounded-tl-sm bubble-tail-left shadow-sm"
                        }`}
                      >
                        <p className="text-[14.2px] text-[#111b21] dark:text-[var(--foreground)] whitespace-pre-wrap leading-[19px] break-words">
                          {msg.content}
                        </p>
                        <div className="flex items-center justify-end gap-1 mt-1 -mb-0.5">
                          <span className="text-[11px] text-[#667781]/70 tabular-nums">
                            {new Date(msg.created_at).toLocaleTimeString("es-AR", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                          {msg.role === "assistant" && (
                            <DoubleCheck className="text-[#53bdeb] ml-0.5" />
                          )}
                          {msg.role === "user" && (
                            <SingleCheck className="text-[#667781]/50 ml-0.5" />
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Typing indicator */}
            {sending && (
              <div className="flex justify-start mb-0.5 animate-msg-fade">
                <div className="bg-[var(--bubble-incoming)] rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm bubble-tail-left">
                  <div className="flex items-center gap-1.5">
                    <div className="typing-dot w-2 h-2 bg-[#667781] rounded-full" />
                    <div className="typing-dot w-2 h-2 bg-[#667781] rounded-full" />
                    <div className="typing-dot w-2 h-2 bg-[#667781] rounded-full" />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Scroll-to-bottom button with counter */}
        {showScrollBtn && (
          <button
            onClick={() => scrollToBottom()}
            className="scroll-bottom-btn"
            aria-label="Ir al final"
          >
            {newMsgCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-[#364c85] text-white text-[10px] font-bold flex items-center justify-center badge-pulse">
                {newMsgCount}
              </span>
            )}
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#667781" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
        )}
      </div>

      {/* ── Input Area ────────────────────────────────── */}
      <div className="bg-white dark:bg-[var(--card)] border-t border-[#e9edef] dark:border-[var(--border)] px-4 py-3">
        {/* Sim phone indicator */}
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[11px] text-[#667781]">Simulando como:</span>
          <input
            value={simPhone}
            onChange={(e) => setSimPhone(e.target.value)}
            className="input-stick px-2.5 py-1 text-xs bg-[#f0f2f5] rounded-lg text-[#111b21] w-36 focus:outline-none tabular-nums"
            placeholder="1155551234"
          />
        </div>
        {/* Message input */}
        <div className="flex items-center gap-3">
          <input
            ref={inputRef}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Escribi un mensaje como paciente..."
            disabled={sending}
            className="input-stick flex-1 px-4 py-2.5 bg-[#f0f2f5] rounded-2xl text-sm text-[#111b21] placeholder-[#667781]/50 focus:outline-none disabled:opacity-50"
          />
          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={sending || !inputText.trim()}
            className="send-btn w-11 h-11 rounded-full bg-[#364c85] text-white flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed flex-shrink-0 shadow-md shadow-[#364c85]/20"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
