"use client";

import { createContext, useContext, useEffect, useRef, useState, useCallback } from "react";
import { adminWs } from "@/lib/ws";
import { WsEvent } from "@/lib/types";

interface NotificationContextValue {
  soundEnabled: boolean;
  browserEnabled: boolean;
  toggleSound: () => void;
  toggleBrowser: () => void;
  activeConversationId: number | null;
  setActiveConversation: (id: number | null) => void;
}

const NotificationContext = createContext<NotificationContextValue>({
  soundEnabled: true,
  browserEnabled: false,
  toggleSound: () => {},
  toggleBrowser: () => {},
  activeConversationId: null,
  setActiveConversation: () => {},
});

export function useNotifications() {
  return useContext(NotificationContext);
}

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [browserEnabled, setBrowserEnabled] = useState(false);
  const activeConvRef = useRef<number | null>(null);
  const [activeConversationId, setActiveConversationIdState] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Load preferences from localStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    const savedSound = localStorage.getItem("notif_sound");
    const savedBrowser = localStorage.getItem("notif_browser");
    if (savedSound !== null) setSoundEnabled(savedSound === "true");
    if (savedBrowser !== null) setBrowserEnabled(savedBrowser === "true");

    // Create audio element with a simple beep (data URI)
    audioRef.current = new Audio(
      "data:audio/wav;base64,UklGRiQBAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQABAAAAAAD//wAA//8AAAAAAP//AAAAAAAA//8AAP//AAAAAP//AAD//wAAAAD//wAA//8AAAAAAP//AAAAAAAA//8AAP//AAAAAP//AAD//wAAAAD//wAAAAAAAP//AAD//wAAAAD//wAA//8AAAAAAP//AAAAAAAA"
    );
    audioRef.current.volume = 0.3;
  }, []);

  const setActiveConversation = useCallback((id: number | null) => {
    activeConvRef.current = id;
    setActiveConversationIdState(id);
  }, []);

  const toggleSound = useCallback(() => {
    setSoundEnabled((prev) => {
      const next = !prev;
      localStorage.setItem("notif_sound", String(next));
      return next;
    });
  }, []);

  const toggleBrowser = useCallback(async () => {
    if (!browserEnabled) {
      // Request permission
      if ("Notification" in window && Notification.permission !== "granted") {
        const perm = await Notification.requestPermission();
        if (perm !== "granted") return;
      }
      setBrowserEnabled(true);
      localStorage.setItem("notif_browser", "true");
    } else {
      setBrowserEnabled(false);
      localStorage.setItem("notif_browser", "false");
    }
  }, [browserEnabled]);

  // Listen for new messages
  useEffect(() => {
    const unsub = adminWs.on("new_message", (event: WsEvent) => {
      // Don't notify for the currently active conversation
      if (event.conversation_id === activeConvRef.current) return;
      // Don't notify for bot messages (only user messages matter for admin)
      if (event.message?.role === "assistant") return;

      // Play sound
      if (soundEnabled && audioRef.current) {
        audioRef.current.currentTime = 0;
        audioRef.current.play().catch(() => {});
      }

      // Browser notification
      if (browserEnabled && "Notification" in window && Notification.permission === "granted") {
        const body = event.message?.content?.substring(0, 100) || "Nuevo mensaje";
        new Notification("STICK - Nuevo mensaje", {
          body,
          icon: "/stick-icon-white.png",
          tag: `conv-${event.conversation_id}`,
        });
      }
    });
    return unsub;
  }, [soundEnabled, browserEnabled]);

  return (
    <NotificationContext.Provider
      value={{
        soundEnabled,
        browserEnabled,
        toggleSound,
        toggleBrowser,
        activeConversationId,
        setActiveConversation,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}
