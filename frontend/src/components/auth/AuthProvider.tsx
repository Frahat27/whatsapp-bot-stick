"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { AdminUser, TokenResponse } from "@/lib/types";
import { api } from "@/lib/api";
import { adminWs } from "@/lib/ws";

interface AuthContextType {
  admin: AdminUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  admin: null,
  isAuthenticated: false,
  isLoading: true,
  login: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [admin, setAdmin] = useState<AdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    const adminStr = localStorage.getItem("admin");
    if (token && adminStr) {
      try {
        const parsed = JSON.parse(adminStr);
        setAdmin({ ...parsed, token });
        adminWs.connect(token);
      } catch {
        localStorage.removeItem("token");
        localStorage.removeItem("admin");
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (username: string, password: string) => {
    const response = await api.login(username, password);
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Login failed");
    }
    const data: TokenResponse = await response.json();
    const user: AdminUser = {
      username,
      name: data.admin_name,
      phone: data.admin_phone,
      token: data.access_token,
    };
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("admin", JSON.stringify({ username, name: user.name, phone: user.phone }));
    setAdmin(user);
    adminWs.connect(data.access_token);
    router.push("/dashboard");
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("admin");
    adminWs.disconnect();
    setAdmin(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ admin, isAuthenticated: !!admin, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
