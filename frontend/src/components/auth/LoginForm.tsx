"use client";

import { useState } from "react";
import { useAuth } from "./AuthProvider";

export function LoginForm() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error de login");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-sm">
      {/* Logo & Title */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center mb-4 logo-pulse">
          <img src="/stick-logo-white.png" alt="STICK" className="h-16 drop-shadow-lg" />
        </div>
        <p className="text-white/60 text-sm mt-1.5 font-light tracking-wide">Panel de Administracion</p>
      </div>

      {/* Login Card — Glassmorphism */}
      <div className="glass-card rounded-2xl p-8">
        <div className="text-center mb-6">
          <h2 className="text-lg font-semibold text-[#364c85]">Bienvenido</h2>
          <p className="text-sm text-[#667781] mt-1">Ingresa tus credenciales para continuar</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="username" className="block text-xs font-semibold text-[#364c85] uppercase tracking-wider">
              Usuario
            </label>
            <input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Tu usuario"
              required
              className="input-stick w-full px-4 py-2.5 bg-[#f0f2f5] rounded-xl text-[#111b21] placeholder-[#667781]/60 focus:outline-none text-sm"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="block text-xs font-semibold text-[#364c85] uppercase tracking-wider">
              Contrasena
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Tu contrasena"
              required
              className="input-stick w-full px-4 py-2.5 bg-[#f0f2f5] rounded-xl text-[#111b21] placeholder-[#667781]/60 focus:outline-none text-sm"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200/60 text-red-600 text-sm px-4 py-2.5 rounded-xl flex items-center gap-2">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !username.trim() || !password.trim()}
            className="btn-stick w-full py-3 bg-[#364c85] hover:bg-[#2a3d6e] text-white font-semibold rounded-xl disabled:opacity-40 disabled:cursor-not-allowed mt-2 shadow-lg shadow-[#364c85]/20"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Ingresando...
              </span>
            ) : (
              "Ingresar"
            )}
          </button>
        </form>

        <div className="flex items-center gap-2 justify-center mt-6">
          <div className="w-1.5 h-1.5 rounded-full bg-[#e7f1ac]" />
          <p className="text-xs text-[#667781]">
            Bot Sofia v2.0 — STICK Alineadores
          </p>
        </div>
      </div>
    </div>
  );
}
