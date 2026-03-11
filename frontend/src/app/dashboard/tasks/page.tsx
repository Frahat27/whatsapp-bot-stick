"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface Task {
  _row_number: number;
  "Fecha Creación": string;
  Tipo: string;
  Prioridad: string;
  Paciente: string;
  "Teléfono": string;
  "ID Paciente": string;
  Profesional: string;
  Contexto: string;
  Estado: string;
  "Resuelta por": string;
  "Fecha Resolución": string;
  "Notas Resolución": string;
}

const statusTabs = [
  { value: "Pendiente", label: "Pendientes", color: "bg-orange-500" },
  { value: "En proceso", label: "En proceso", color: "bg-blue-500" },
  { value: "Resuelto", label: "Resueltas", color: "bg-emerald-500" },
];

const typeColors: Record<string, string> = {
  "Urgencia": "bg-red-100 text-red-700 border-red-200",
  "Coordinación Endodoncia": "bg-purple-100 text-purple-700 border-purple-200",
  "Coordinación Implantes": "bg-indigo-100 text-indigo-700 border-indigo-200",
  "Coordinación Cirugía": "bg-pink-100 text-pink-700 border-pink-200",
  "Reprogramación": "bg-amber-100 text-amber-700 border-amber-200",
  "Sin disponibilidad": "bg-gray-100 text-gray-700 border-gray-200",
  "Consulta sin respuesta": "bg-[#95b2ee]/15 text-[#364c85] border-[#95b2ee]/25",
  "Factura pendiente": "bg-emerald-100 text-emerald-700 border-emerald-200",
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("Pendiente");
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [resolveNotes, setResolveNotes] = useState("");
  const [resolving, setResolving] = useState<number | null>(null);
  const router = useRouter();

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getTasks(activeTab);
      if (res.ok) {
        const data = await res.json();
        setTasks(data.tasks || []);
      }
    } catch (e) {
      console.error("Failed to fetch tasks:", e);
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleResolve = async (rowNumber: number, estado: string) => {
    setResolving(rowNumber);
    try {
      const res = await api.resolveTask(rowNumber, {
        estado,
        notas: resolveNotes || undefined,
      });
      if (res.ok) {
        setResolveNotes("");
        setExpandedRow(null);
        fetchTasks();
      }
    } catch (e) {
      console.error("Failed to resolve task:", e);
    } finally {
      setResolving(null);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "2-digit" });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="flex h-full w-full">
      {/* Left nav — matches ConversationList width */}
      <div className="hidden md:flex md:w-[380px] flex-shrink-0 bg-white dark:bg-[var(--card)] border-r border-[#e9edef] dark:border-[var(--border)] flex-col">
        {/* Header */}
        <div className="sidebar-header flex items-center justify-between px-4 py-3.5">
          <div className="flex items-center gap-3">
            <img src="/stick-icon-white.png" alt="STICK" className="w-8 h-8 drop-shadow-sm" />
            <div>
              <span className="text-white font-semibold text-sm">Tareas Pendientes</span>
              <span className="block text-white/50 text-[10px] font-light">Google Sheets</span>
            </div>
          </div>
          <button
            onClick={() => router.push("/dashboard")}
            className="text-white/60 hover:text-white transition-all p-2 rounded-xl hover:bg-white/10"
            title="Volver a conversaciones"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </button>
        </div>

        {/* Tab filters */}
        <div className="px-3 py-3 space-y-2 bg-white dark:bg-[var(--card)]">
          {statusTabs.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setActiveTab(tab.value)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                activeTab === tab.value
                  ? "bg-[#364c85]/10 text-[#364c85]"
                  : "text-[#667781] hover:bg-[#f0f2f5]"
              }`}
            >
              <span className={`w-2.5 h-2.5 rounded-full ${tab.color}`} />
              {tab.label}
              {activeTab === tab.value && !loading && (
                <span className="ml-auto text-xs bg-[#364c85] text-white rounded-full px-2 py-0.5">
                  {tasks.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Summary stats */}
        <div className="mt-auto px-4 py-4 border-t border-[#e9edef] dark:border-[var(--border)]">
          <button
            onClick={fetchTasks}
            className="w-full text-xs text-[#667781] hover:text-[#364c85] transition-colors py-2"
          >
            Actualizar lista
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto wa-scrollbar bg-[#f0f2f5] dark:bg-[var(--chat-panel-bg)] animate-page-enter">
        {/* Mobile header */}
        <div className="md:hidden flex items-center gap-2 px-4 py-3 bg-white dark:bg-[var(--card)] border-b border-[#e9edef]">
          <button onClick={() => router.push("/dashboard")} className="p-1">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#364c85" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <h1 className="font-semibold text-[#111b21]">Tareas Pendientes</h1>
          {/* Mobile tabs */}
          <div className="ml-auto flex gap-1">
            {statusTabs.map((tab) => (
              <button
                key={tab.value}
                onClick={() => setActiveTab(tab.value)}
                className={`text-[10px] px-2 py-1 rounded-full font-medium ${
                  activeTab === tab.value
                    ? "bg-[#364c85] text-white"
                    : "bg-[#f0f2f5] text-[#667781]"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tasks list */}
        <div className="max-w-4xl mx-auto p-4 space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between mb-2">
            <h2 className="hidden md:block text-lg font-bold text-[#111b21] dark:text-[var(--foreground)]">
              {statusTabs.find((t) => t.value === activeTab)?.label} ({tasks.length})
            </h2>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-2xl p-5 shadow-sm">
                  <div className="space-y-3">
                    <div className="skeleton-stick h-4 w-1/3 rounded-full" />
                    <div className="skeleton-stick h-3 w-2/3 rounded-full" />
                    <div className="skeleton-stick h-3 w-1/2 rounded-full" />
                  </div>
                </div>
              ))}
            </div>
          ) : tasks.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-[#667781]">
              <div className="w-16 h-16 rounded-2xl bg-white flex items-center justify-center mb-4 shadow-sm">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="opacity-40">
                  <path d="M9 11l3 3L22 4" />
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                </svg>
              </div>
              <p className="text-sm font-medium">No hay tareas {activeTab.toLowerCase()}</p>
            </div>
          ) : (
            tasks.map((task) => {
              const isExpanded = expandedRow === task._row_number;
              const isUrgent = task.Prioridad?.includes("Alta");
              const tc = typeColors[task.Tipo] || "bg-[#f0f2f5] text-[#667781] border-[#e9edef]";

              return (
                <div
                  key={task._row_number}
                  className={`bg-white dark:bg-[var(--card)] rounded-2xl shadow-sm transition-all duration-200 overflow-hidden ${
                    isUrgent ? "ring-1 ring-red-200" : ""
                  } ${isExpanded ? "shadow-md" : "hover:shadow-md"}`}
                >
                  {/* Task header — clickable */}
                  <div
                    onClick={() => setExpandedRow(isExpanded ? null : task._row_number)}
                    className="flex items-start gap-3 px-5 py-4 cursor-pointer"
                  >
                    {/* Priority indicator */}
                    <div className={`mt-1 w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                      isUrgent ? "bg-red-500" : "bg-yellow-400"
                    }`} />

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${tc}`}>
                          {task.Tipo}
                        </span>
                        {isUrgent && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500 text-white font-bold">
                            URGENTE
                          </span>
                        )}
                        <span className="text-[11px] text-[#667781] ml-auto flex-shrink-0">
                          {formatDate(task["Fecha Creación"])}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-[#111b21] dark:text-[var(--foreground)] mt-1.5 line-clamp-2">
                        {task.Contexto}
                      </p>
                      <div className="flex items-center gap-3 mt-1.5 text-xs text-[#667781]">
                        {task.Paciente && <span>{task.Paciente}</span>}
                        {task.Profesional && (
                          <span className="flex items-center gap-1">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                              <circle cx="12" cy="7" r="4" />
                            </svg>
                            {task.Profesional}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Expand chevron */}
                    <svg
                      width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#667781" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                      className={`flex-shrink-0 mt-1 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                    >
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>

                  {/* Expanded details */}
                  {isExpanded && (
                    <div className="px-5 pb-4 border-t border-[#e9edef] dark:border-[var(--border)] pt-3 animate-msg-fade">
                      {/* Full details */}
                      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs mb-4">
                        {task.Paciente && (
                          <div>
                            <span className="text-[#667781]">Paciente:</span>
                            <span className="ml-1 text-[#111b21] dark:text-[var(--foreground)] font-medium">{task.Paciente}</span>
                          </div>
                        )}
                        {task["Teléfono"] && (
                          <div>
                            <span className="text-[#667781]">Telefono:</span>
                            <span className="ml-1 text-[#111b21] dark:text-[var(--foreground)] tabular-nums">{task["Teléfono"]}</span>
                          </div>
                        )}
                        {task["ID Paciente"] && (
                          <div>
                            <span className="text-[#667781]">ID:</span>
                            <span className="ml-1 text-[#111b21] dark:text-[var(--foreground)] tabular-nums">{task["ID Paciente"]}</span>
                          </div>
                        )}
                        {task.Profesional && (
                          <div>
                            <span className="text-[#667781]">Profesional:</span>
                            <span className="ml-1 text-[#111b21] dark:text-[var(--foreground)]">{task.Profesional}</span>
                          </div>
                        )}
                      </div>

                      {/* Context full */}
                      <div className="bg-[#f0f2f5] dark:bg-[var(--muted)] rounded-xl p-3 mb-4">
                        <p className="text-xs text-[#111b21] dark:text-[var(--foreground)] leading-relaxed whitespace-pre-wrap">
                          {task.Contexto}
                        </p>
                      </div>

                      {/* Resolution notes (for resolved) */}
                      {task["Notas Resolución"] && (
                        <div className="bg-emerald-50 rounded-xl p-3 mb-4">
                          <p className="text-xs text-emerald-800">
                            <span className="font-semibold">Resuelto por {task["Resuelta por"]}</span>
                            {task["Fecha Resolución"] && ` el ${task["Fecha Resolución"]}`}
                          </p>
                          <p className="text-xs text-emerald-700 mt-1">{task["Notas Resolución"]}</p>
                        </div>
                      )}

                      {/* Action buttons (only for non-resolved) */}
                      {activeTab !== "Resuelto" && (
                        <div className="space-y-2">
                          <textarea
                            value={resolveNotes}
                            onChange={(e) => setResolveNotes(e.target.value)}
                            placeholder="Notas de resolucion (opcional)..."
                            rows={2}
                            className="input-stick w-full px-3 py-2 bg-[#f0f2f5] rounded-xl text-xs text-[#111b21] placeholder-[#667781]/50 focus:outline-none resize-none"
                          />
                          <div className="flex gap-2">
                            {activeTab === "Pendiente" && (
                              <button
                                onClick={() => handleResolve(task._row_number, "En proceso")}
                                disabled={resolving === task._row_number}
                                className="btn-stick text-[11px] px-4 py-2 rounded-xl bg-blue-500 text-white font-medium disabled:opacity-50"
                              >
                                En proceso
                              </button>
                            )}
                            <button
                              onClick={() => handleResolve(task._row_number, "Resuelto")}
                              disabled={resolving === task._row_number}
                              className="btn-stick text-[11px] px-4 py-2 rounded-xl bg-emerald-500 text-white font-medium disabled:opacity-50"
                            >
                              {resolving === task._row_number ? "Guardando..." : "Resolver"}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
