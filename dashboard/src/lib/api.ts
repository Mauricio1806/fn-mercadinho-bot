/**
 * API client — Axios com interceptors JWT e tipagem forte.
 */

import axios, { AxiosError, type AxiosInstance } from "axios";
import type {
  MyTenant,
  TenantConfig,
  DashboardStats,
  ConsolidatedStats,
  SalesEntry,
  Order,
  OrderStatus,
  Product,
  IntegrationConfig,
  SyncResult,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "";

export const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

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
          if (error.config) {
            error.config.headers.Authorization = `Bearer ${access_token}`;
            return api.request(error.config);
          }
        } catch {
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

// ── Auth ───────────────────────────────────────────────────────────────
export async function login(email: string, password: string) {
  const resp = await api.post<{ access_token: string; refresh_token: string }>(
    "/api/auth/login",
    { email, password }
  );
  return resp.data;
}

// ── Dashboard ──────────────────────────────────────────────────────────
export async function getStats(): Promise<DashboardStats> {
  const resp = await api.get<DashboardStats>("/api/dashboard/stats");
  return resp.data;
}

export async function getConsolidatedStats(): Promise<ConsolidatedStats> {
  const resp = await api.get<ConsolidatedStats>("/api/dashboard/consolidated");
  return resp.data;
}

export async function getSales(limit = 50): Promise<SalesEntry[]> {
  const resp = await api.get<SalesEntry[]>("/api/dashboard/sales", {
    params: { limit },
  });
  return resp.data;
}

// ── Pedidos ────────────────────────────────────────────────────────────
export async function getOrders(params?: {
  status_filter?: OrderStatus;
  limit?: number;
  offset?: number;
}): Promise<Order[]> {
  const resp = await api.get<Order[]>("/api/orders/", { params });
  return resp.data;
}

export async function getOrder(orderId: string): Promise<Order> {
  const resp = await api.get<Order>(`/api/orders/${orderId}`);
  return resp.data;
}

export async function updateOrderStatus(
  orderId: string,
  status: OrderStatus
): Promise<Order> {
  const resp = await api.patch<Order>(`/api/orders/${orderId}/status`, { status });
  return resp.data;
}

// ── Produtos ───────────────────────────────────────────────────────────
export async function getProducts(): Promise<Product[]> {
  const resp = await api.get<Product[]>("/api/products/");
  return resp.data;
}

// ── Integrações ────────────────────────────────────────────────────────
export async function getIntegrationConfig(
  tenantId: string
): Promise<IntegrationConfig> {
  const resp = await api.get<IntegrationConfig>(
    `/api/integrations/${tenantId}/config`
  );
  return resp.data;
}

export async function updateIntegrationConfig(
  tenantId: string,
  body: Partial<IntegrationConfig> & { api_key?: string }
): Promise<IntegrationConfig> {
  const resp = await api.put<IntegrationConfig>(
    `/api/integrations/${tenantId}/config`,
    body
  );
  return resp.data;
}

export async function triggerSync(tenantId: string): Promise<SyncResult> {
  const resp = await api.post<SyncResult>(`/api/integrations/${tenantId}/sync`);
  return resp.data;
}

export async function importCSV(
  tenantId: string,
  file: File
): Promise<SyncResult> {
  const formData = new FormData();
  formData.append("file", file);
  const resp = await api.post<SyncResult>(
    `/api/integrations/${tenantId}/csv`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return resp.data;
}

// ── Tenants (superadmin) ───────────────────────────────────────────────
export async function getTenants() {
  const resp = await api.get("/api/tenants/");
  return resp.data;
}


// ── Tenant self (tenant_admin gerencia o próprio) ──────────────────────
export async function getMyTenant(): Promise<MyTenant> {
  const resp = await api.get<MyTenant>("/api/tenants/me");
  return resp.data;
}

export async function updateMyTenant(
  body: { name?: string; config?: Partial<TenantConfig> }
): Promise<MyTenant> {
  const resp = await api.put<MyTenant>("/api/tenants/me", body);
  return resp.data;
}
