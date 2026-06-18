/**
 * TenantDashboard — visão geral do tenant logado.
 *
 * - 4 KPIs (pedidos, faturamento dia, faturamento semana, pendentes)
 * - Gráfico de área 7 dias (recharts) — agrupa /sales por data client-side
 * - Tabela das últimas 8 vendas confirmadas
 * - Estados completos: loading skeleton / empty / error com retry
 */

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  ShoppingBag,
  DollarSign,
  TrendingUp,
  Clock,
  AlertCircle,
  RefreshCw,
  Users,
  Inbox,
} from "lucide-react";
import { getStats, getSales } from "@/lib/api";
import { formatBRL, formatTime, formatDate } from "@/lib/format";
import type { DashboardStats, SalesEntry } from "@/lib/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Skeleton } from "@/components/ui/Skeleton";

interface DayPoint {
  date: string;   // dd/MM
  iso: string;    // YYYY-MM-DD
  revenue: number;
  orders: number;
}

function build7DayChart(sales: SalesEntry[]): DayPoint[] {
  const days: DayPoint[] = [];
  const today = new Date();
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const iso = d.toISOString().slice(0, 10);
    days.push({
      date: d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }),
      iso,
      revenue: 0,
      orders: 0,
    });
  }
  const byIso = new Map(days.map((d) => [d.iso, d]));
  for (const s of sales) {
    const iso = s.created_at.slice(0, 10);
    const day = byIso.get(iso);
    if (day) {
      day.revenue += s.total;
      day.orders += 1;
    }
  }
  return days;
}

export function TenantDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [sales, setSales] = useState<SalesEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([getStats(), getSales(50)])
      .then(([s, sl]) => {
        if (cancelled) return;
        setStats(s);
        setSales(sl);
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(
          e?.response?.data?.detail ??
            e?.message ??
            "Falha ao carregar dashboard."
        );
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const chartData = useMemo(() => build7DayChart(sales), [sales]);
  const recent = useMemo(() => sales.slice(0, 8), [sales]);
  const chartEmpty = chartData.every((d) => d.revenue === 0);

  return (
    <>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Visão geral do seu negócio</p>
        </div>
        <button
          className="btn btn-ghost"
          onClick={() => setRefreshKey((k) => k + 1)}
          disabled={loading}
        >
          <RefreshCw
            size={14}
            style={loading ? { animation: "spin 1s linear infinite" } : undefined}
          />
          Atualizar
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div
          style={{
            background: "rgba(239,68,68,0.10)",
            border: "1px solid rgba(239,68,68,0.30)",
            borderRadius: "var(--radius-sm)",
            padding: "12px 16px",
            color: "var(--color-error)",
            marginBottom: 24,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <AlertCircle size={16} />
          <span style={{ flex: 1 }}>{error}</span>
          <button
            className="btn btn-ghost"
            style={{ padding: "4px 10px", fontSize: 12 }}
            onClick={() => setRefreshKey((k) => k + 1)}
          >
            Tentar de novo
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="stats-grid">
        <KpiCard
          loading={loading}
          icon={<ShoppingBag size={16} />}
          label="Pedidos hoje"
          value={stats ? String(stats.orders_today) : "—"}
          sub={stats ? `${stats.sales_today} confirmados` : ""}
        />
        <KpiCard
          loading={loading}
          icon={<DollarSign size={16} />}
          label="Faturamento hoje"
          value={stats ? formatBRL(stats.revenue_today) : "—"}
          sub={stats ? `Comissão ${formatBRL(stats.commission_today)}` : ""}
        />
        <KpiCard
          loading={loading}
          icon={<TrendingUp size={16} />}
          label="Faturamento 7 dias"
          value={stats ? formatBRL(stats.revenue_week) : "—"}
          sub={stats ? `Comissão ${formatBRL(stats.commission_week)}` : ""}
        />
        <KpiCard
          loading={loading}
          icon={<Clock size={16} />}
          label="Pedidos pendentes"
          value={stats ? String(stats.pending_orders) : "—"}
          sub={stats ? `${stats.total_customers} clientes na base` : ""}
        />
      </div>

      {/* Chart */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 16,
          }}
        >
          <div>
            <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>
              Faturamento — últimos 7 dias
            </h2>
            <p style={{
              fontSize: 12,
              color: "var(--color-text-muted)",
              margin: "2px 0 0",
            }}>
              Somente vendas confirmadas
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{
              display: "inline-block",
              width: 8,
              height: 8,
              borderRadius: 2,
              background: "var(--color-primary)",
            }} />
            <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
              Receita (R$)
            </span>
          </div>
        </div>

        {loading ? (
          <Skeleton height={260} />
        ) : chartEmpty ? (
          <EmptyState
            icon={<Inbox size={28} />}
            title="Sem vendas nos últimos 7 dias"
            subtitle="Quando o bot fechar uma venda, ela aparece aqui."
          />
        ) : (
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <AreaChart
                data={chartData}
                margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="revFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--color-border)" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) =>
                    v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v)
                  }
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--color-surface-2)",
                    border: "1px solid var(--color-border)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "var(--color-text)" }}
                  formatter={(v: number) => [formatBRL(v), "Receita"]}
                />
                <Area
                  type="monotone"
                  dataKey="revenue"
                  stroke="var(--color-primary)"
                  strokeWidth={2}
                  fill="url(#revFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Recent orders */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{
          padding: "18px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid var(--color-border)",
        }}>
          <div>
            <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>
              Vendas recentes
            </h2>
            <p style={{
              fontSize: 12,
              color: "var(--color-text-muted)",
              margin: "2px 0 0",
            }}>
              Últimos pedidos confirmados
            </p>
          </div>
          <button className="btn btn-ghost" onClick={() => navigate("/orders")}>
            Ver todos
          </button>
        </div>

        {loading ? (
          <div style={{
            padding: 20,
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}>
            {[...Array(5)].map((_, i) => <Skeleton key={i} height={32} />)}
          </div>
        ) : recent.length === 0 ? (
          <EmptyState
            icon={<Users size={28} />}
            title="Nenhum pedido por aqui ainda"
            subtitle="Assim que o bot fechar a primeira venda, ela aparece nesta lista."
          />
        ) : (
          <div className="table-wrapper" style={{ border: "none", borderRadius: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Pedido</th>
                  <th>Cliente</th>
                  <th>Itens</th>
                  <th>Total</th>
                  <th>Status</th>
                  <th>Quando</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((s) => {
                  const created = new Date(s.created_at);
                  const isToday =
                    created.toDateString() === new Date().toDateString();
                  return (
                    <tr key={s.id}>
                      <td style={{ fontFamily: "monospace", fontSize: 12 }}>
                        {s.id}
                      </td>
                      <td>{s.customer}</td>
                      <td style={{
                        color: "var(--color-text-muted)",
                        fontSize: 12,
                      }}>
                        {s.items.length} item{s.items.length !== 1 ? "s" : ""}
                      </td>
                      <td style={{ fontWeight: 600 }}>{formatBRL(s.total)}</td>
                      <td><StatusBadge status={s.status} /></td>
                      <td style={{
                        color: "var(--color-text-muted)",
                        fontSize: 12,
                      }}>
                        {isToday ? formatTime(s.created_at) : formatDate(s.created_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

// ── Subcomponentes ─────────────────────────────────────────────────────

interface KpiCardProps {
  loading: boolean;
  icon: ReactNode;
  label: string;
  value: string;
  sub: string;
}

function KpiCard({ loading, icon, label, value, sub }: KpiCardProps) {
  return (
    <div className="card stat-card">
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <span className="stat-label">{label}</span>
        <span style={{ color: "var(--color-text-muted)" }}>{icon}</span>
      </div>
      {loading ? (
        <>
          <Skeleton width={120} height={28} style={{ marginTop: 4 }} />
          <Skeleton width={90} height={12} style={{ marginTop: 8 }} />
        </>
      ) : (
        <>
          <span className="stat-value">{value}</span>
          <span className="stat-sub">{sub}</span>
        </>
      )}
    </div>
  );
}

function EmptyState({
  icon,
  title,
  subtitle,
}: {
  icon: ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <div style={{
      padding: "40px 20px",
      textAlign: "center",
      color: "var(--color-text-muted)",
    }}>
      <div style={{
        display: "inline-flex",
        width: 56,
        height: 56,
        borderRadius: 16,
        background: "var(--color-surface-2)",
        alignItems: "center",
        justifyContent: "center",
        marginBottom: 12,
      }}>
        {icon}
      </div>
      <div style={{
        fontSize: 14,
        fontWeight: 600,
        color: "var(--color-text)",
      }}>
        {title}
      </div>
      <div style={{ fontSize: 12, marginTop: 4 }}>{subtitle}</div>
    </div>
  );
}
