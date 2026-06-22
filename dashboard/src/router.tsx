/**
 * App router — todo usuário autenticado vai pra /dashboard.
 * Plataforma é gerida via /settings (seletor multi-tenant pro platform owner).
 */

import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Login } from "@/pages/Login";
import { TenantDashboard } from "@/pages/tenant/Dashboard";
import { Orders } from "@/pages/tenant/Orders";
import { Products } from "@/pages/tenant/Products";
import { Settings } from "@/pages/tenant/Settings";
import { isAuthenticated } from "@/lib/auth";
import { AppLayout } from "@/components/Layout/AppLayout";
import { useState } from "react";
import { Customers } from "@/pages/tenant/Customers";
import { Conversations } from "@/pages/tenant/Conversations";
import { Ajuda } from "@/pages/tenant/Ajuda";

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RoleRedirect() {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  return <Navigate to="/dashboard" replace />;
}

function UnderConstruction({ page }: { page: string }) {
  return (
    <div style={{ padding: 60, textAlign: "center", color: "var(--color-text-muted)" }}>
      <div style={{
        display: "inline-flex", width: 64, height: 64, borderRadius: 18,
        background: "var(--color-surface-2)", alignItems: "center",
        justifyContent: "center", fontSize: 28, marginBottom: 16,
      }}>🚧</div>
      <h1 style={{ color: "var(--color-text)", fontSize: 22, margin: "0 0 8px" }}>{page}</h1>
      <p style={{ fontSize: 14, margin: 0 }}>Em construção.</p>
    </div>
  );
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

        <Route path="/conversations" element={<RequireAuth><AppLayout><Conversations /></AppLayout></RequireAuth>} />
        <Route path="/customers" element={<RequireAuth><AppLayout><Customers /></AppLayout></RequireAuth>} />
        <Route path="/settings" element={<RequireAuth><AppLayout><Settings /></AppLayout></RequireAuth>} />
        <Route path="/ajuda" element={<RequireAuth><AppLayout><Ajuda /></AppLayout></RequireAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
