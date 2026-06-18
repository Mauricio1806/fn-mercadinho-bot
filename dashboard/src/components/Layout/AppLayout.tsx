/**
 * AppLayout — sidebar com navegação + bloco do usuário + logout.
 * Itens de menu se adaptam ao role (tenant_admin vs superadmin).
 */

import { NavLink } from "react-router-dom";
import { useBranding } from "@/providers/BrandingProvider";
import { getCurrentUser, isSuperAdmin, logout } from "@/lib/auth";
import {
  LayoutDashboard,
  ShoppingBag,
  MessageCircle,
  Package,
  Users,
  Settings as SettingsIcon,
  Webhook,
  Building2,
  LogOut,
} from "lucide-react";
import type { ReactNode } from "react";

interface NavLinkItem {
  to: string;
  label: string;
  icon: ReactNode;
}

const tenantNav: NavLinkItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: <LayoutDashboard size={16} /> },
  { to: "/orders", label: "Pedidos", icon: <ShoppingBag size={16} /> },
  { to: "/conversations", label: "Conversas", icon: <MessageCircle size={16} /> },
  { to: "/products", label: "Produtos", icon: <Package size={16} /> },
  { to: "/customers", label: "Clientes", icon: <Users size={16} /> },
  { to: "/settings", label: "Configurações", icon: <SettingsIcon size={16} /> },
];

const adminNav: NavLinkItem[] = [
  { to: "/admin/dashboard", label: "Visão Geral", icon: <LayoutDashboard size={16} /> },
  { to: "/admin/tenants", label: "Tenants", icon: <Building2 size={16} /> },
  { to: "/admin/webhooks", label: "Webhooks", icon: <Webhook size={16} /> },
];

export function AppLayout({ children }: { children: ReactNode }) {
  const branding = useBranding();
  const user = getCurrentUser();
  const isAdmin = isSuperAdmin();
  const items = isAdmin ? adminNav : tenantNav;

  return (
    <div className="app-layout">
      <aside className="sidebar">
        {/* Brand */}
        <div className="sidebar-logo">
          {branding.logoUrl ? (
            <img
              src={branding.logoUrl}
              alt={branding.tenantName}
              style={{ width: 36, height: 36, borderRadius: 10, objectFit: "cover" }}
            />
          ) : (
            <div className="sidebar-logo-icon">
              {branding.tenantName.charAt(0).toUpperCase()}
            </div>
          )}
          <span className="sidebar-logo-text">{branding.tenantName}</span>
        </div>

        {/* Nav */}
        <nav style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
          {items.map((it) => (
            <NavLink
              key={it.to}
              to={it.to}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              {it.icon}
              <span>{it.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Usuário + logout */}
        <div style={{
          borderTop: "1px solid var(--color-border)",
          paddingTop: 16,
          marginTop: 16,
        }}>
          <div style={{
            padding: "0 12px 12px",
            fontSize: 12,
            color: "var(--color-text-muted)",
          }}>
            <div style={{
              fontWeight: 600,
              color: "var(--color-text)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}>
              {user?.full_name ?? "—"}
            </div>
            <div style={{ marginTop: 2 }}>
              {isAdmin ? "Superadmin" : "Administrador"}
            </div>
          </div>
          <button
            className="nav-item"
            onClick={logout}
            style={{ color: "var(--color-error)" }}
          >
            <LogOut size={16} />
            <span>Sair</span>
          </button>
        </div>
      </aside>

      <main className="main-content">{children}</main>
    </div>
  );
}
