import { WsEvent } from "./types";

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace("http", "ws");

type EventHandler = (data: WsEvent) => void;

class AdminWebSocket {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<EventHandler>> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private token: string = "";

  connect(token: string) {
    this.token = token;
    this.cleanup();

    this.ws = new WebSocket(`${WS_BASE}/api/v1/admin/ws?token=${token}`);

    this.ws.onopen = () => {
      console.log("[WS] Connected");
      this.pingTimer = setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send("ping");
        }
      }, 30000);
    };

    this.ws.onmessage = (event) => {
      try {
        const data: WsEvent = JSON.parse(event.data);
        if (data.type === "pong") return;
        const handlers = this.listeners.get(data.type);
        if (handlers) {
          handlers.forEach((handler) => handler(data));
        }
        // Also notify "all" listeners
        const allHandlers = this.listeners.get("*");
        if (allHandlers) {
          allHandlers.forEach((handler) => handler(data));
        }
      } catch (e) {
        console.error("[WS] Parse error:", e);
      }
    };

    this.ws.onclose = () => {
      console.log("[WS] Disconnected, reconnecting in 3s...");
      this.cleanup();
      this.reconnectTimer = setTimeout(() => this.connect(this.token), 3000);
    };

    this.ws.onerror = (error) => {
      console.error("[WS] Error:", error);
    };
  }

  on(eventType: string, handler: EventHandler): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(handler);
    return () => {
      this.listeners.get(eventType)?.delete(handler);
    };
  }

  disconnect() {
    this.cleanup();
    this.ws?.close();
    this.ws = null;
  }

  private cleanup() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }
}

// Singleton
export const adminWs = new AdminWebSocket();
