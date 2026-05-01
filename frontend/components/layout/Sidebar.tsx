"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ShoppingCart,
  MessageSquare,
  Package,
  Users,
  BarChart3,
  LogOut,
  Store,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/pedidos", label: "Pedidos", icon: ShoppingCart },
  { href: "/conversas", label: "Conversas", icon: MessageSquare },
  { href: "/produtos", label: "Produtos", icon: Package },
  { href: "/clientes", label: "Clientes", icon: Users },
  { href: "/relatorios", label: "Relatórios", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();
  const logout = useAuthStore((s) => s.logout);
  const [open, setOpen] = useState(false);

  const SidebarContent = () => (
    <aside className="flex h-full w-60 flex-col border-r bg-white">
      <div className="flex items-center gap-2 border-b px-6 py-5">
        <Store className="h-6 w-6 text-blue-600" />
        <div>
          <p className="font-semibold text-gray-900 leading-tight">FN Mercadinho</p>
          <p className="text-xs text-gray-400">Dashboard Admin</p>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 p-3">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t p-3">
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 hover:bg-red-50 hover:text-red-700 transition-colors"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          Sair
        </button>
      </div>
    </aside>
  );

  return (
    <>
      {/* Mobile: botão hamburguer */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 flex items-center gap-3 bg-white border-b px-4 py-3">
        <button onClick={() => setOpen(true)} className="p-1">
          <Menu className="h-5 w-5 text-gray-700" />
        </button>
        <Store className="h-5 w-5 text-blue-600" />
        <span className="font-semibold text-gray-900 text-sm">FN Mercadinho</span>
      </div>

      {/* Mobile: overlay */}
      {open && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/40"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Mobile: drawer */}
      <div className={cn(
        "md:hidden fixed inset-y-0 left-0 z-50 transition-transform duration-300",
        open ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="relative h-full">
          <button
            onClick={() => setOpen(false)}
            className="absolute top-4 right-3 z-10 p-1"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
          <SidebarContent />
        </div>
      </div>

      {/* Desktop: sidebar fixa */}
      <div className="hidden md:flex h-screen">
        <SidebarContent />
      </div>
    </>
  );
}
