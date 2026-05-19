/**
 * Layout principal com sidebar e header.
 */

import { type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, ShoppingCart, Package, Users, MessageCircle, LogOut
} from "lucide-react";
import { useBranding } from "@/providers/BrandingProvider";
import { logout, isSuperAdmin } from "@/lib/auth";

const TENANT_NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/orders", label: "Pedidos", icon: ShoppingCart },
  { href: "/products", label: "Produtos", icon: Package },
  { href: "/customers", label: "Clientes", icon: Users },
  { href: "/conversations", label: "Conversas", icon: MessageCircle },
];

const ADMIN_NAV = [
  { href: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard },
];

export function AppLayout({ children }: { children: ReactNode }) {
  const { tenantName, corPrimaria, logoUrl } = useBranding();
  const { pathname } = useLocation();
  const isAdmin = isSuperAdmin();
  const navItems = isAdmin ? ADMIN_NAV : TENANT_NAV;

  return (
    <div className="app-layout">
      <aside className="sidebar">
        {/* Logo */}
        <div className="sidebar-logo">
          {logoUrl ? (
            <img src={logoUrl} alt={tenantName} style={{ width: 36, height: 36, borderRadius: 10, objectFit: "cover" }} />
          ) : (
            <div className="sidebar-logo-icon" style={{ background: corPrimaria }}>
              {tenantName.charAt(0)}
            </div>
          )}
          <span className="sidebar-logo-text">{tenantName}</span>
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1 }}>
          {navItems.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              to={href}
              className={`nav-item ${pathname === href ? "active" : ""}`}
              id={`nav-${href.replace("/", "").replace("/", "-")}`}
            >
              <Icon size={17} />
              {label}
            </Link>
          ))}
        </nav>

        {/* Logout */}
        <button id="btn-logout" className="nav-item" onClick={logout} style={{ marginTop: "auto" }}>
          <LogOut size={17} />
          Sair
        </button>
      </aside>

      <main className="main-content">
        {children}
      </main>
    </div>
  );
}
