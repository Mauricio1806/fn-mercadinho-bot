"use client";

import { create } from "zustand";
import { authApi } from "@/lib/api";
import type { LoginRequest } from "@/lib/types";

interface AuthState {
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  login: (creds: LoginRequest) => Promise<boolean>;
  logout: () => void;
  initialize: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  loading: false,
  error: null,

  initialize: () => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("access_token");
    set({ isAuthenticated: !!token });
  },

  login: async (creds) => {
    set({ loading: true, error: null });
    try {
      const tokens = await authApi.login(creds);
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      set({ isAuthenticated: true, loading: false });
      return true;
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ isAuthenticated: false });
    window.location.href = "/login";
  },
}));
