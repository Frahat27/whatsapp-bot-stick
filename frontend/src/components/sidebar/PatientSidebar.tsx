"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { ConversationDetail } from "@/lib/types";

const contactTypeLabels: Record<string, { text: string; color: string }> = {
  paciente: { text: "Paciente", color: "bg-[#364c85] text-white" },
  lead: { text: "Lead", color: "bg-[#95b2ee] text-white" },
  nuevo: { text: "Nuevo", color: "bg-[#e7f1ac] text-[#2a3a1e]" },
  admin: { text: "Admin", color: "bg-orange-100 text-orange-700" },
};

const statusLabels: Record<string, { text: string; color: string }> = {
  bot_active: { text: "Sofia activa", color: "text-emerald-600" },
  escalated: { text: "Escalada", color: "text-yellow-600" },
  admin_takeover: { text: "Admin takeover", color: "text-orange-600" },
};

/* ── Label colors (deterministic by hash) ─── */
const labelColors = [
  "bg-[#364c85]/10 text-[#364c85] border-[#364c85]/20",
  "bg-[#95b2ee]/15 text-[#4a6fb5] border-[#95b2ee]/25",
  "bg-[#e7f1ac]/40 text-[#3a5a1e] border-[#c5d98a]/40",
  "bg-orange-50 text-orange-700 border-orange-200",
  "bg-purple-50 text-purple-700 border-purple-200",
  "bg-rose-50 text-rose-700 border-rose-200",
];

const suggestedLabels = ["urgente", "seguimiento", "vip", "reclamo", "nuevo_turno", "cobro"];

function getLabelColor(label: string): string {
  let hash = 0;
  for (let i = 0; i < label.length; i++) hash = label.charCodeAt(i) + ((hash << 5) - hash);
  return labelColors[Math.abs(hash) % labelColors.length];
}

function getInitials(name: string | null, phone: string): string {
  if (name) {
    const parts = name.split(/[,\s]+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.substring(0, 2).toUpperCase();
  }
  return phone.slice(-2);
}

export function PatientSidebar({
  detail,
  onDetailUpdate,
}: {
  detail: ConversationDetail | null;
  onDetailUpdate: (d: ConversationDetail) => void;
}) {
  /* ── Notes state ─── */
  const [editingNotes, setEditingNotes] = useState(false);
  const [notesText, setNotesText] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);

  /* ── Labels state ─── */
  const [labelInput, setLabelInput] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [savingLabels, setSavingLabels] = useState(false);

  if (!detail) {
    return (
      <div className="flex items-center justify-center h-full text-[#667781] text-sm">
        Cargando...
      </div>
    );
  }

  const ct = detail.contact_type ? contactTypeLabels[detail.contact_type] : null;
  const st = statusLabels[detail.status] || { text: detail.status, color: "text-gray-500" };

  /* ── Notes handlers ─── */
  const startEditNotes = () => {
    setNotesText(detail.admin_notes || "");
    setEditingNotes(true);
  };

  const saveNotes = async () => {
    setSavingNotes(true);
    try {
      await api.updateState(detail.id, { admin_notes: notesText });
      onDetailUpdate({ ...detail, admin_notes: notesText });
      setEditingNotes(false);
    } catch (e) {
      console.error("Failed to save notes:", e);
    } finally {
      setSavingNotes(false);
    }
  };

  /* ── Label handlers ─── */
  const addLabel = async (label: string) => {
    const trimmed = label.trim().toLowerCase();
    if (!trimmed || detail.labels.includes(trimmed)) return;
    const newLabels = [...detail.labels, trimmed];
    setSavingLabels(true);
    try {
      await api.updateState(detail.id, { labels: newLabels });
      onDetailUpdate({ ...detail, labels: newLabels });
      setLabelInput("");
    } catch (e) {
      console.error("Failed to add label:", e);
    } finally {
      setSavingLabels(false);
    }
  };

  const removeLabel = async (label: string) => {
    const newLabels = detail.labels.filter((l) => l !== label);
    setSavingLabels(true);
    try {
      await api.updateState(detail.id, { labels: newLabels });
      onDetailUpdate({ ...detail, labels: newLabels });
    } catch (e) {
      console.error("Failed to remove label:", e);
    } finally {
      setSavingLabels(false);
    }
  };

  const handleLabelKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addLabel(labelInput);
    }
  };

  const availableSuggestions = suggestedLabels.filter((s) => !detail.labels.includes(s));

  return (
    <div className="flex flex-col h-full overflow-y-auto wa-scrollbar bg-white dark:bg-[var(--card)]">
      {/* ── Header with avatar ─── */}
      <div className="flex flex-col items-center pt-8 pb-5 px-4 border-b border-[#e9edef] dark:border-[var(--border)]">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#364c85] to-[#5a7bc4] flex items-center justify-center shadow-lg mb-3">
          <span className="text-white font-bold text-2xl">
            {getInitials(detail.patient_name, detail.phone)}
          </span>
        </div>
        <h3 className="font-bold text-[#111b21] dark:text-[var(--foreground)] text-base">
          {detail.patient_name || "Sin nombre"}
        </h3>
        <span className="text-[#667781] text-sm tabular-nums mt-0.5">{detail.phone}</span>
        <div className="flex items-center gap-2 mt-2.5">
          {ct && (
            <span className={`text-[11px] px-2.5 py-1 rounded-full font-semibold ${ct.color}`}>
              {ct.text}
            </span>
          )}
          <span className={`text-[11px] font-semibold ${st.color}`}>
            {st.text}
          </span>
        </div>
      </div>

      {/* ── Contact Info ─── */}
      <div className="px-4 py-4 border-b border-[#e9edef] dark:border-[var(--border)]">
        <h4 className="text-[11px] font-bold text-[#364c85] uppercase tracking-wider mb-3">
          Datos del contacto
        </h4>
        <div className="space-y-2.5">
          {detail.patient_id && (
            <div className="flex justify-between text-sm">
              <span className="text-[#667781]">ID Paciente</span>
              <span className="text-[#111b21] dark:text-[var(--foreground)] font-medium text-xs tabular-nums">
                {detail.patient_id}
              </span>
            </div>
          )}
          {detail.lead_id && (
            <div className="flex justify-between text-sm">
              <span className="text-[#667781]">ID Lead</span>
              <span className="text-[#111b21] dark:text-[var(--foreground)] font-medium text-xs tabular-nums">
                {detail.lead_id}
              </span>
            </div>
          )}
          <div className="flex justify-between text-sm">
            <span className="text-[#667781]">Activa</span>
            <span className={detail.is_active ? "text-emerald-600 font-medium" : "text-[#667781]"}>
              {detail.is_active ? "Si" : "No"}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-[#667781]">Creada</span>
            <span className="text-[#111b21] dark:text-[var(--foreground)] text-xs">
              {new Date(detail.created_at).toLocaleDateString("es-AR", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
              })}
            </span>
          </div>
        </div>
      </div>

      {/* ── Labels ─── */}
      <div className="px-4 py-4 border-b border-[#e9edef] dark:border-[var(--border)]">
        <h4 className="text-[11px] font-bold text-[#364c85] uppercase tracking-wider mb-3">
          Etiquetas
        </h4>

        {/* Current labels */}
        <div className="flex flex-wrap gap-1.5 mb-2.5">
          {detail.labels.map((label) => (
            <span
              key={label}
              className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full font-medium border ${getLabelColor(label)}`}
            >
              {label}
              <button
                onClick={() => removeLabel(label)}
                disabled={savingLabels}
                className="hover:opacity-70 ml-0.5"
              >
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </span>
          ))}
          {detail.labels.length === 0 && (
            <span className="text-[11px] text-[#667781]/60 italic">Sin etiquetas</span>
          )}
        </div>

        {/* Add label input */}
        <div className="relative">
          <input
            value={labelInput}
            onChange={(e) => setLabelInput(e.target.value)}
            onKeyDown={handleLabelKeyDown}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder="Agregar etiqueta..."
            disabled={savingLabels}
            className="input-stick w-full px-3 py-1.5 bg-[#f0f2f5] rounded-lg text-xs text-[#111b21] placeholder-[#667781]/50 focus:outline-none"
          />
        </div>

        {/* Suggestions */}
        {showSuggestions && availableSuggestions.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {availableSuggestions.map((s) => (
              <button
                key={s}
                onMouseDown={(e) => { e.preventDefault(); addLabel(s); }}
                className="text-[10px] px-2 py-0.5 rounded-full bg-[#f0f2f5] text-[#667781] hover:bg-[#e4e6e8] hover:text-[#111b21] transition-colors"
              >
                + {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Admin Notes ─── */}
      <div className="px-4 py-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-[11px] font-bold text-[#364c85] uppercase tracking-wider">
            Notas internas
          </h4>
          {!editingNotes && (
            <button
              onClick={startEditNotes}
              className="text-[#667781] hover:text-[#364c85] transition-colors"
              title="Editar notas"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
            </button>
          )}
        </div>

        {editingNotes ? (
          <div className="space-y-2">
            <textarea
              value={notesText}
              onChange={(e) => setNotesText(e.target.value)}
              rows={4}
              className="input-stick w-full px-3 py-2 bg-[#f0f2f5] rounded-lg text-xs text-[#111b21] placeholder-[#667781]/50 focus:outline-none resize-none"
              placeholder="Escribi notas internas sobre esta conversacion..."
              autoFocus
            />
            <div className="flex gap-2">
              <button
                onClick={saveNotes}
                disabled={savingNotes}
                className="btn-stick text-[11px] px-3 py-1.5 rounded-lg bg-[#364c85] text-white font-medium disabled:opacity-50"
              >
                {savingNotes ? "Guardando..." : "Guardar"}
              </button>
              <button
                onClick={() => setEditingNotes(false)}
                className="text-[11px] px-3 py-1.5 rounded-lg bg-[#f0f2f5] text-[#667781] font-medium hover:bg-[#e4e6e8]"
              >
                Cancelar
              </button>
            </div>
          </div>
        ) : (
          <p className={`text-xs leading-relaxed ${detail.admin_notes ? "text-[#111b21] dark:text-[var(--foreground)]" : "text-[#667781]/60 italic"}`}>
            {detail.admin_notes || "Sin notas. Hace click en el lapiz para agregar."}
          </p>
        )}
      </div>
    </div>
  );
}
