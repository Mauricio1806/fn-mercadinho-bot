/**
 * API client — Axios com interceptors JWT e base URL configurável.
 */

import axios, { AxiosError, type AxiosInstance } from "axios";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

// ── Interceptor: injeta token JWT em todo request ──────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Interceptor: trata 401 e redireciona para login ───────────────────
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const resp = await axios.post(`${BASE_URL}/api/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const { access_token, refresh_token } = resp.data;
          localStorage.setItem("access_token", access_token);
          localStorage.setItem("refresh_token", refresh_token);

          // Retry da requisição original
          if (error.config) {
            error.config.headers.Authorization = `Bearer ${access_token}`;
            return api.request(error.config);
          }
        } catch {
          // Refresh falhou — limpa sessão
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
      } else {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ── Helpers tipados ────────────────────────────────────────────────────

export async function login(email: string, password: string) {
  const resp = await api.post<{
    access_token: string;
    refresh_token: string;
  }>("/api/auth/login", { email, password });
  return resp.data;
}

export async function getStats() {
  const resp = await api.get("/api/dashboard/stats");
  return resp.data;
}

export async function getOrders(params?: Record<string, unknown>) {
  const resp = await api.get("/api/orders/", { params });
  return resp.data;
}

export async function updateOrderStatus(orderId: string, status: string) {
  const resp = await api.patch(`/api/orders/${orderId}/status`, { status });
  return resp.data;
}

export async function getProducts() {
  const resp = await api.get("/api/products/");
  return resp.data;
}

export async function importCSV(tenantId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const resp = await api.post(`/api/integrations/${tenantId}/csv`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return resp.data;
}

export async function getTenants() {
  const resp = await api.get("/api/tenants/");
  return resp.data;
}

export async function getConsolidatedStats() {
  const resp = await api.get("/api/dashboard/consolidated");
  return resp.data;
}
