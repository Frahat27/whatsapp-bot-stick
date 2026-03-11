"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { adminWs } from "@/lib/ws";
import { ConversationListItem, WsEvent } from "@/lib/types";
import { useAuth } from "@/components/auth/AuthProvider";
import { useNotifications } from "@/components/notifications/NotificationProvider";

const statusColors: Record<string, { bg: string; cls: string }> = {
  bot_active: { bg: "bg-green-500", cls: "online" },
  escalated: { bg: "bg-yellow-500", cls: "escalated" },
  admin_takeover: { bg: "bg-orange-500", cls: "takeover" },
};

const contactTypeLabels: Record<string, { text: string; color: string }> = {
  paciente: { text: "Paciente", color: "bg-[#364c85] text-white" },
  lead: { text: "Lead", color: "bg-[#95b2ee] text-white" },
  nuevo: { text: "Nuevo", color: "bg-[#e7f1ac] text-[#2a3a1e]" },
  admin: { text: "Admin", color: "bg-orange-100 text-orange-700" },
};

// Avatar color palette for variety
const avatarColors = [
  "from-[#364c85] to-[#5a7bc4]",
  "from-[#95b2ee] to-[#6b8fd9]",
  "from-[#7c6bc4] to-[#a78bfa]",
  "from-[#2a8a6e] to-[#34d399]",
  "from-[#c4786b] to-[#f0a090]",
  "from-[#8b6bc4] to-[#c49dff]",
];

function getAvatarColor(id: number): string {
  return avatarColors[id % avatarColors.length];
}

function getInitials(name: string | null, phone: string): string {
  if (name) {
    const parts = name.split(/[,\s]+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.substring(0, 2).toUpperCase();
  }
  return phone.slice(-2);
}

const statusFilters = [
  { value: "", label: "Todas" },
  { value: "bot_active", label: "Bot" },
  { value: "escalated", label: "Escalada" },
  { value: "admin_takeover", label: "Admin" },
];

const typeFilters = [
  { value: "", label: "Todos" },
  { value: "paciente", label: "Paciente" },
  { value: "lead", label: "Lead" },
  { value: "nuevo", label: "Nuevo" },
];

export function ConversationList({ activeId }: { activeId?: number }) {
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [search, setSearch] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const { admin, logout } = useAuth();
  const { soundEnabled, browserEnabled, toggleSound, toggleBrowser } = useNotifications();
  const [showNotifMenu, setShowNotifMenu] = useState(false);
  const router = useRouter();

  const fetchConversations = async () => {
    try {
      const params: Record<string, string> = {};
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.contact_type = typeFilter;
      const res = await api.getConversations(params);
      if (res.ok) {
        setConversations(await res.json());
      }
    } catch (e) {
      console.error("Failed to fetch conversations:", e);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [search, statusFilter, typeFilter]);

  useEffect(() => {
    const unsub = adminWs.on("*", (event: WsEvent) => {
      if (event.type === "new_message" || event.type === "state_changed") {
        fetchConversations();
      }
    });
    return unsub;
  }, [search]);

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    const now = new Date();
    if (d.toDateString() === now.toDateString()) {
      return d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
    }
    return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit" });
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header — STICK branding with gradient */}
      <div className="sidebar-header flex items-center justify-between px-4 py-3.5">
        <div className="flex items-center gap-3">
          <img src="/stick-icon-white.png" alt="STICK" className="w-8 h-8 drop-shadow-sm" />
          <div>
            <span className="text-white font-semibold text-sm">{admin?.name || "Admin"}</span>
            <span className="block text-white/50 text-[10px] font-light">STICK Admin Panel</span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {/* Tasks link */}
          <button
            onClick={() => router.push("/dashboard/tasks")}
            className="text-white/60 hover:text-white transition-all p-2 rounded-xl hover:bg-white/10"
            title="Tareas pendientes"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
          </button>
          {/* Notification settings */}
          <div className="relative">
            <button
              onClick={() => setShowNotifMenu((s) => !s)}
              className={`p-2 rounded-xl transition-all ${
                soundEnabled || browserEnabled
                  ? "text-white/90 hover:text-white hover:bg-white/10"
                  : "text-white/40 hover:text-white/70 hover:bg-white/10"
              }`}
              title="Notificaciones"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
            </button>
            {showNotifMenu && (
              <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-xl shadow-lg border border-[#e9edef] z-50 overflow-hidden animate-msg-fade">
                <button
                  onClick={toggleSound}
                  className="flex items-center justify-between w-full px-3 py-2.5 text-xs text-[#111b21] hover:bg-[#f0f2f5] transition-colors"
                >
                  <span>Sonido</span>
                  <span className={`w-8 h-4 rounded-full transition-colors ${soundEnabled ? "bg-[#364c85]" : "bg-[#d1d5db]"} relative`}>
                    <span className={`absolute top-0.5 ${soundEnabled ? "right-0.5" : "left-0.5"} w-3 h-3 rounded-full bg-white transition-all shadow-sm`} />
                  </span>
                </button>
                <button
                  onClick={toggleBrowser}
                  className="flex items-center justify-between w-full px-3 py-2.5 text-xs text-[#111b21] hover:bg-[#f0f2f5] transition-colors"
                >
                  <span>Notificaciones</span>
                  <span className={`w-8 h-4 rounded-full transition-colors ${browserEnabled ? "bg-[#364c85]" : "bg-[#d1d5db]"} relative`}>
                    <span className={`absolute top-0.5 ${browserEnabled ? "right-0.5" : "left-0.5"} w-3 h-3 rounded-full bg-white transition-all shadow-sm`} />
                  </span>
                </button>
              </div>
            )}
          </div>
          {/* Logout */}
          <button
            onClick={logout}
            className="text-white/60 hover:text-white transition-all p-2 rounded-xl hover:bg-white/10"
            title="Cerrar sesion"
          >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
        </div>
      </div>

      {/* Search + Filter toggle */}
      <div className="px-3 py-2 bg-white dark:bg-[var(--card)]">
        <div className="relative flex items-center gap-2">
          <div className="relative flex-1">
            <svg
              className={`absolute left-3 top-1/2 -translate-y-1/2 transition-colors duration-200 ${searchFocused ? "text-[#364c85]" : "text-[#667781]"}`}
              width="16" height="16" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              placeholder="Buscar o iniciar chat"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
              className="input-stick w-full pl-10 pr-4 py-2 bg-[#f0f2f5] rounded-xl text-sm text-[#111b21] placeholder-[#667781]/60 focus:outline-none"
            />
          </div>
          <button
            onClick={() => setShowFilters((f) => !f)}
            className={`p-2 rounded-xl transition-all ${
              showFilters || statusFilter || typeFilter
                ? "bg-[#364c85]/10 text-[#364c85]"
                : "text-[#667781] hover:bg-[#f0f2f5]"
            }`}
            title="Filtros"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
            </svg>
          </button>
        </div>

        {/* Filter pills */}
        {showFilters && (
          <div className="mt-2 space-y-1.5 animate-msg-fade">
            <div className="flex flex-wrap gap-1">
              {statusFilters.map((f) => (
                <button
                  key={f.value}
                  onClick={() => setStatusFilter(f.value)}
                  className={`text-[10px] px-2.5 py-1 rounded-full font-medium transition-all ${
                    statusFilter === f.value
                      ? "bg-[#364c85] text-white"
                      : "bg-[#f0f2f5] text-[#667781] hover:bg-[#e4e6e8]"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-1">
              {typeFilters.map((f) => (
                <button
                  key={f.value}
                  onClick={() => setTypeFilter(f.value)}
                  className={`text-[10px] px-2.5 py-1 rounded-full font-medium transition-all ${
                    typeFilter === f.value
                      ? "bg-[#364c85] text-white"
                      : "bg-[#f0f2f5] text-[#667781] hover:bg-[#e4e6e8]"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Conversations */}
      <div className="flex-1 overflow-y-auto wa-scrollbar bg-white dark:bg-[var(--card)]">
        {conversations.map((conv) => {
          const isActive = activeId === conv.id;
          const ct = conv.contact_type ? contactTypeLabels[conv.contact_type] : null;
          const hasUnread = conv.status === "escalated";
          const statusInfo = statusColors[conv.status] || { bg: "bg-gray-300", cls: "" };
          return (
            <div
              key={conv.id}
              onClick={() => router.push(`/dashboard/conversations/${conv.id}`)}
              className={`conv-item flex items-center gap-3 px-4 py-3 cursor-pointer ${
                isActive ? "active" : ""
              }`}
            >
              {/* Avatar with gradient */}
              <div className={`relative w-12 h-12 rounded-full bg-gradient-to-br ${getAvatarColor(conv.id)} flex items-center justify-center flex-shrink-0 shadow-sm`}>
                <span className="text-white font-semibold text-sm">
                  {getInitials(conv.patient_name, conv.phone)}
                </span>
                {/* Status indicator dot */}
                <div className={`status-dot ${statusInfo.cls} absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-[2.5px] border-white ${statusInfo.bg}`} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className={`text-[15px] truncate ${hasUnread ? "font-bold text-[#111b21]" : "font-semibold text-[#111b21]"}`}>
                    {conv.patient_name || conv.phone}
                  </span>
                  <span className={`text-[11px] flex-shrink-0 ml-2 ${hasUnread ? "text-[#364c85] font-semibold" : "text-[#667781]"}`}>
                    {formatTime(conv.last_message_at)}
                  </span>
                </div>
                <div className="flex items-center justify-between mt-0.5">
                  <p className={`text-[13px] truncate ${hasUnread ? "text-[#111b21] font-medium" : "text-[#667781]"}`}>
                    {conv.last_message_preview || "Sin mensajes"}
                  </p>
                  <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                    {hasUnread && (
                      <span className="badge-pulse w-5 h-5 rounded-full bg-[#364c85] text-white text-[10px] font-bold flex items-center justify-center">
                        !
                      </span>
                    )}
                    {ct && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${ct.color}`}>
                        {ct.text}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
        {conversations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-[#667781]">
            <div className="w-16 h-16 rounded-2xl bg-[#f0f2f5] flex items-center justify-center mb-4">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="opacity-40">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <p className="text-sm font-medium">No hay conversaciones</p>
            <p className="text-xs mt-1 text-[#667781]/60">Usa el simulador para empezar</p>
          </div>
        )}
      </div>
    </div>
  );
}
