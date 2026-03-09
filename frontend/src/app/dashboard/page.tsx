"use client";

import { useState } from "react";
import { ConversationList } from "@/components/conversations/ConversationList";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function DashboardPage() {
  const [testPhone, setTestPhone] = useState("");
  const [testMessage, setTestMessage] = useState("");
  const [sending, setSending] = useState(false);
  const router = useRouter();

  const handleNewTest = async () => {
    if (!testPhone.trim() || !testMessage.trim()) return;
    setSending(true);
    try {
      const res = await api.simulate(testPhone, testMessage);
      if (res.ok) {
        const data = await res.json();
        router.push(`/dashboard/conversations/${data.conversation_id}`);
      }
    } catch (e) {
      console.error("Test failed:", e);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex h-full w-full">
      {/* Sidebar */}
      <div className="w-[380px] flex-shrink-0 bg-white dark:bg-[var(--card)] border-r border-[#e9edef] dark:border-[var(--border)]">
        <ConversationList />
      </div>
      {/* Main area — Empty state */}
      <div className="flex-1 flex flex-col items-center justify-center bg-[#f0f2f5] dark:bg-[var(--chat-panel-bg)] animate-page-enter">
        <div className="max-w-md w-full text-center space-y-8 px-8">
          {/* STICK logo animated */}
          <div className="flex flex-col items-center gap-4">
            <div className="animate-breathe">
              <img src="/stick-logo-blue.png" alt="STICK" className="h-20 drop-shadow-md" />
            </div>
            <div>
              <h2 className="text-[#111b21] dark:text-[var(--foreground)] text-xl font-semibold">STICK Admin Panel</h2>
              <p className="text-[#667781] dark:text-[var(--muted-foreground)] text-sm leading-relaxed max-w-sm mt-2">
                Envia y recibe mensajes de pacientes. Usa el simulador de testing
                para probar el flujo completo del Bot Sofia.
              </p>
            </div>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-gradient-to-r from-transparent via-[#e9edef] to-transparent" />
            <span className="text-[10px] text-[#667781] font-semibold uppercase tracking-widest">Simulador</span>
            <div className="flex-1 h-px bg-gradient-to-l from-transparent via-[#e9edef] to-transparent" />
          </div>

          {/* Test Simulator */}
          <div className="space-y-3 text-left">
            <div>
              <label className="text-[10px] font-semibold text-[#364c85] uppercase tracking-wider">
                Telefono a simular
              </label>
              <input
                value={testPhone}
                onChange={(e) => setTestPhone(e.target.value)}
                placeholder="1155551234"
                className="input-stick mt-1.5 w-full px-4 py-2.5 bg-white dark:bg-[var(--card)] rounded-xl text-sm text-[#111b21] dark:text-[var(--foreground)] placeholder-[#667781]/50 focus:outline-none border border-[#e9edef] dark:border-[var(--border)]"
              />
            </div>
            <div>
              <label className="text-[10px] font-semibold text-[#364c85] uppercase tracking-wider">
                Mensaje
              </label>
              <input
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleNewTest()}
                placeholder="Hola, quiero sacar un turno"
                className="input-stick mt-1.5 w-full px-4 py-2.5 bg-white dark:bg-[var(--card)] rounded-xl text-sm text-[#111b21] dark:text-[var(--foreground)] placeholder-[#667781]/50 focus:outline-none border border-[#e9edef] dark:border-[var(--border)]"
              />
            </div>
            <button
              onClick={handleNewTest}
              disabled={sending || !testPhone.trim() || !testMessage.trim()}
              className="btn-stick w-full py-2.5 bg-[#364c85] hover:bg-[#2a3d6e] text-white text-sm font-semibold rounded-xl disabled:opacity-30 disabled:cursor-not-allowed shadow-md shadow-[#364c85]/15"
            >
              {sending ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Enviando...
                </span>
              ) : (
                "Iniciar conversacion de prueba"
              )}
            </button>
          </div>

          <p className="text-xs text-[#667781]/60">
            O selecciona una conversacion del panel izquierdo
          </p>
        </div>
      </div>
    </div>
  );
}
