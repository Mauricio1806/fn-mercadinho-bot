/**
 * Dashboard principal do tenant — stats + últimas vendas.
 */

import { useQuery } from "@tanstack/react-query";
import { getStats, getOrders } from "@/lib/api";
import { useBranding } from "@/providers/BrandingProvider";
import { ShoppingCart, Users, TrendingUp, Clock } from "lucide-react";

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: typeof ShoppingCart;
  color: string;
}) {
  return (
    <div className="card stat-card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div className="stat-label">{label}</div>
          <div className="stat-value">{value}</div>
          {sub && <div className="stat-sub">{sub}</div>}
        </div>
        <div
          style={{
            padding: "10px",
            borderRadius: "10px",
            background: `${color}15`,
          }}
        >
          <Icon size={22} color={color} />
        </div>
      </div>
    </div>
  );
}

const STATUS_LABELS: Record<string, string> = {
  pending: "Aguardando PIX",
  payment_confirmed: "PIX Confirmado",
  preparing: "Preparando",
  ready: "Pronto",
  delivering: "Em Entrega",
  delivered: "Entregue",
  cancelled: "Cancelado",
};

export function TenantDashboard() {
  const { tenantName, corPrimaria } = useBranding();

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
    refetchInterval: 30_000, // Atualiza a cada 30s
  });

  const { data: orders, isLoading: ordersLoading } = useQuery({
    queryKey: ["orders", "recent"],
    queryFn: () => getOrders({ limit: 10 }),
    refetchInterval: 15_000,
  });

  const fmtCurrency = (n: number) =>
    n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">{tenantName} — visão geral de hoje</p>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <StatCard
          label="Pedidos hoje"
          value={statsLoading ? "—" : stats?.orders_today ?? 0}
          sub="todos os status"
          icon={ShoppingCart}
          color={corPrimaria}
        />
        <StatCard
          label="Faturamento hoje"
          value={statsLoading ? "—" : fmtCurrency(stats?.revenue_today ?? 0)}
          sub="vendas confirmadas"
          icon={TrendingUp}
          color="#22C55E"
        />
        <StatCard
          label="Clientes"
          value={statsLoading ? "—" : stats?.total_customers ?? 0}
          sub="base total"
          icon={Users}
          color="#A855F7"
        />
        <StatCard
          label="Pendentes agora"
          value={statsLoading ? "—" : stats?.pending_orders ?? 0}
          sub="aguardando ação"
          icon={Clock}
          color="#F59E0B"
        />
      </div>

      {/* Últimos pedidos */}
      <div className="card" style={{ padding: 0 }}>
        <div
          style={{
            padding: "16px 24px",
            borderBottom: "1px solid var(--color-border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h2 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Últimos Pedidos</h2>
          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
            Atualiza automaticamente
          </span>
        </div>

        <div className="table-wrapper" style={{ border: "none", borderRadius: 0 }}>
          <table>
            <thead>
              <tr>
                <th>Pedido</th>
                <th>Cliente</th>
                <th>Itens</th>
                <th>Total</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {ordersLoading ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", padding: 32, color: "var(--color-text-muted)" }}>
                    Carregando...
                  </td>
                </tr>
              ) : !orders?.length ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", padding: 32, color: "var(--color-text-muted)" }}>
                    Nenhum pedido ainda hoje 🎉
                  </td>
                </tr>
              ) : (
                orders.map((order: any) => (
                  <tr key={order.id}>
                    <td style={{ fontFamily: "monospace", fontSize: 12 }}>
                      #{String(order.id).slice(0, 8).toUpperCase()}
                    </td>
                    <td>{order.customer_id?.toString().slice(0, 8)}</td>
                    <td>{order.items?.length ?? 0} item(s)</td>
                    <td style={{ fontWeight: 600 }}>
                      {fmtCurrency(order.total_amount)}
                    </td>
                    <td>
                      <span className={`badge badge-${order.status}`}>
                        {STATUS_LABELS[order.status] ?? order.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Comissão */}
      {stats && (
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div>
              <div className="stat-label">Comissão da Plataforma — Semana</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: corPrimaria, marginTop: 4 }}>
                {fmtCurrency(stats.commission_week ?? 0)}
              </div>
            </div>
            <div>
              <div className="stat-label">Faturamento — Semana</div>
              <div style={{ fontSize: 22, fontWeight: 700, marginTop: 4 }}>
                {fmtCurrency(stats.revenue_week ?? 0)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
