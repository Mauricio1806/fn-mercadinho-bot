"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, initialize } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (!isAuthenticated) {
      const token = localStorage.getItem("access_token");
      if (!token) router.push("/login");
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated && typeof window !== "undefined" && !localStorage.getItem("access_token")) {
    return null;
  }

  return <>{children}</>;
}
