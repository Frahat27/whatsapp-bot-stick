"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#d0d9f6] dark:bg-[var(--background)]">
        <div className="flex flex-col items-center gap-4">
          <img src="/stick-icon-blue.png" alt="STICK" className="w-14 h-14 animate-pulse drop-shadow-md" />
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-[#364c85] animate-bounce" style={{ animationDelay: "0ms" }} />
            <div className="w-1.5 h-1.5 rounded-full bg-[#364c85] animate-bounce" style={{ animationDelay: "150ms" }} />
            <div className="w-1.5 h-1.5 rounded-full bg-[#364c85] animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen overflow-hidden bg-[#d0d9f6] dark:bg-[var(--background)]">
      {/* Top accent bar — hidden on mobile */}
      <div className="hidden md:block h-[127px] bg-gradient-to-r from-[#2a3d6e] via-[#364c85] to-[#4a63a0] fixed top-0 left-0 right-0 z-0" />
      {/* Main container — full screen on mobile, card on desktop */}
      <div className="relative z-10 flex h-screen md:h-[calc(100vh-20px)] md:mt-[10px] mx-auto max-w-[1600px] md:shadow-2xl md:shadow-[#364c85]/10 md:rounded-lg overflow-hidden">
        {children}
      </div>
    </div>
  );
}
