/**
 * Auth helpers — decode JWT e detecção de role.
 */

import { decodeJwt } from "jose";

export type UserRole = "superadmin" | "tenant_admin" | "tenant_viewer";

export interface JWTPayload {
  sub: string;
  role: UserRole;
  tenant_id: string | null;
  email: string;
  full_name: string;
  must_change_password?: boolean;
  branding: {
    cor_primaria: string;
    cor_secundaria: string;
    logo_url: string | null;
    tenant_name: string;
  };
  exp: number;
}

export function getToken(): string | null {
  return localStorage.getItem("access_token");
}

export function getTokenPayload(): JWTPayload | null {
  const token = getToken();
  if (!token) return null;
  try {
    return decodeJwt(token) as JWTPayload;
  } catch {
    return null;
  }
}

export function getCurrentUser(): JWTPayload | null {
  return getTokenPayload();
}

export function isSuperAdmin(): boolean {
  return getCurrentUser()?.role === "superadmin";
}

export function getTenantId(): string | null {
  return getCurrentUser()?.tenant_id ?? null;
}

const DEFAULT_BRANDING = {
  cor_primaria: "#1976D2",
  cor_secundaria: "#FFC107",
  logo_url: null,
  tenant_name: "Mercazap",
};

export function getBranding() {
  // Só usa branding do JWT se o token ainda for válido — senão volta pro default
  if (!isAuthenticated()) return DEFAULT_BRANDING;
  // Platform owner sempre vê "Mercazap", nunca o branding do tenant
  if (isPlatformOwner()) return DEFAULT_BRANDING;
  return getCurrentUser()?.branding ?? DEFAULT_BRANDING;
}

export function isAuthenticated(): boolean {
  const payload = getTokenPayload();
  if (!payload) return false;
  return payload.exp * 1000 > Date.now();
}

export function logout(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login";
}

export function saveTokens(access_token: string, refresh_token: string): void {
  localStorage.setItem("access_token", access_token);
  localStorage.setItem("refresh_token", refresh_token);
}

const PLATFORM_OWNER_TENANT_ID = "00000000-0000-0000-0000-000000000001";

export function isPlatformOwner(): boolean {
  const payload = getTokenPayload();
  if (!payload) return false;
  if (payload.role === "superadmin") return true;
  if (
    payload.role === "tenant_admin" &&
    payload.tenant_id === PLATFORM_OWNER_TENANT_ID
  ) {
    return true;
  }
  return false;
}


export function mustChangePassword(): boolean {
  return getTokenPayload()?.must_change_password === true;
}
