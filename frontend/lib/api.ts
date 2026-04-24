"use client";

import type {
  Customer,
  DashboardStats,
  LoginRequest,
  Order,
  OrderStatus,
  ProductCategory,
  TokenResponse,
  Conversation,
  Message,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── HTTP helpers ──────────────────────────────────────────────────────────────

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    // Token expirado — tenta refresh
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${getToken()}`;
      const retried = await fetch(`${API_URL}${path}`, { ...options, headers });
      if (!retried.ok) throw new Error(`HTTP ${retried.status}`);
      return retried.json() as Promise<T>;
    }
    // Não conseguiu refresh — redireciona para login
    localStorage.clear();
    window.location.href = "/login";
    throw new Error("Sessão expirada");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}

async function tryRefresh(): Promise<boolean> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;

    const data: TokenResponse = await res.json();
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  login: async (body: LoginRequest): Promise<TokenResponse> => {
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? "Erro ao fazer login");
    }
    return res.json();
  },
};

// ── Dashboard ─────────────────────────────────────────────────────────────────

export const dashboardApi = {
  getStats: (): Promise<DashboardStats> =>
    request<DashboardStats>("/api/dashboard/stats"),
};

// ── Orders ────────────────────────────────────────────────────────────────────

export const ordersApi = {
  list: (status?: OrderStatus, limit = 50): Promise<Order[]> => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (status) params.set("status_filter", status);
    return request<Order[]>(`/api/orders/?${params}`);
  },

  get: (id: string): Promise<Order> =>
    request<Order>(`/api/orders/${id}`),

  updateStatus: (id: string, status: OrderStatus): Promise<Order> =>
    request<Order>(`/api/orders/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
};

// ── Products ──────────────────────────────────────────────────────────────────

export const productsApi = {
  listCategories: (): Promise<ProductCategory[]> =>
    request<ProductCategory[]>("/api/products/categories"),

  updateProduct: (
    id: string,
    data: { name?: string; price?: number; is_available?: boolean; stock_quantity?: number }
  ) =>
    request(`/api/products/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

// ── Customers ─────────────────────────────────────────────────────────────────

export const customersApi = {
  list: (limit = 50): Promise<Customer[]> =>
    request<Customer[]>(`/api/customers/?limit=${limit}`),

  toggleBlock: (id: string, is_blocked: boolean): Promise<Customer> =>
    request<Customer>(`/api/customers/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_blocked }),
    }),
};

// ── Conversations ─────────────────────────────────────────────────────────────

export const conversationsApi = {
  list: (limit = 30): Promise<Conversation[]> =>
    request<Conversation[]>(`/api/conversations/?limit=${limit}`),

  getMessages: (id: string): Promise<Message[]> =>
    request<Message[]>(`/api/conversations/${id}/messages`),

  takeover: (id: string): Promise<void> =>
    request(`/api/conversations/${id}/takeover`, { method: "POST" }),
};
