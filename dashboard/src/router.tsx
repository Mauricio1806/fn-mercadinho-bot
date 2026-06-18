/**
 * App router — redireciona por role após login.
 * superadmin → /admin/dashboard
 * tenant_admin | tenant_viewer → /dashboard
 */

import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Login } from "@/pages/Login";
import { TenantDashboard } from "@/pages/tenant/Dashboard";
import { Orders } from "@/pages/tenant/Orders";
import { Products } from "@/pages/tenant/Products";
import { isAuthenticated, isSuperAdmin } from "@/lib/auth";
import { AppLayout } from "@/components/Layout/AppLayout";
import { useState } from "react";

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RoleRedirect() {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  if (isSuperAdmin()) return <Navigate to="/admin/dashboard" replace />;
  return <Navigate to="/dashboard" replace />;
}

export function AppRouter() {
  const [, forceUpdate] = useState(0);

  function handleLogin() {
    forceUpdate(n => n + 1);
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={isAuthenticated() ? <Navigate to="/" replace /> : <Login onSuccess={handleLogin} />} />
        <Route path="/" element={<RoleRedirect />} />

        {/* Tenant Admin */}
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <AppLayout>
                <TenantDashboard />
              </AppLayout>
            </RequireAuth>
          }
        />
        <Route
          path="/orders"
          element={
            <RequireAuth>
              <AppLayout>
                <Orders />
              </AppLayout>
            </RequireAuth>
          }
        />
        <Route
          path="/products"
          element={
            <RequireAuth>
              <AppLayout>
                <Products />
              </AppLayout>
            </RequireAuth>
          }
        />

        {/* Superadmin (stub para Fase 2) */}
        <Route
          path="/admin/dashboard"
          element={
            <RequireAuth>
              <AppLayout>
                <div style={{ padding: 32 }}>
                  <h1 style={{ color: "var(--color-text)" }}>Superadmin Dashboard</h1>
                  <p style={{ color: "var(--color-text-muted)" }}>
                    Visão consolidada de todos os tenants — implementação completa na Fase 2.
                  </p>
                </div>
              </AppLayout>
            </RequireAuth>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
