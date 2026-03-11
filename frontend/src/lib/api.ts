const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchWithAuth(path: string, options: RequestInit = {}) {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (response.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      localStorage.removeItem("admin");
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  return response;
}

export const api = {
  login: async (username: string, password: string) => {
    const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username, password }),
    });
    return response;
  },

  getConversations: (params?: Record<string, string>) => {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    return fetchWithAuth(`/api/v1/admin/conversations${qs}`);
  },

  getConversation: (id: number) =>
    fetchWithAuth(`/api/v1/admin/conversations/${id}`),

  getMessages: (conversationId: number, params?: Record<string, string>) => {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    return fetchWithAuth(
      `/api/v1/admin/conversations/${conversationId}/messages${qs}`
    );
  },

  simulate: (phone: string, content: string, contactName?: string) =>
    fetchWithAuth("/api/v1/admin/simulate", {
      method: "POST",
      body: JSON.stringify({
        phone,
        content,
        contact_name: contactName || "Panel Test",
      }),
    }),

  updateState: (
    conversationId: number,
    data: { status?: string; labels?: string[]; admin_notes?: string }
  ) =>
    fetchWithAuth(`/api/v1/admin/conversations/${conversationId}/state`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  getTasks: (estado: string = "Pendiente") =>
    fetchWithAuth(`/api/v1/admin/tasks?estado=${encodeURIComponent(estado)}`),

  resolveTask: (
    rowNumber: number,
    data: { estado?: string; resuelta_por?: string; notas?: string }
  ) =>
    fetchWithAuth(`/api/v1/admin/tasks/${rowNumber}/resolve`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

export { API_BASE };
