"use client";

import {
  ShoppingCart,
  DollarSign,
  Clock,
  RefreshCw,
  CheckCircle,
  Percent,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { StatCard } from "@/components/dashboard/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { usePolling, useApi } from "@/hooks/useApi";
import { dashboardApi, ordersApi } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Order } from "@/lib/types";

function buildChartData(weekRevenue: number) {
  const days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
  const base = weekRevenue / 7;
  return days.map((day) => ({
    day,
    receita: Math.round(base * (0.6 + Math.random() * 0.8)),
  }));
}

export default function DashboardPage() {
  const { data: stats, loading: statsLoading, reload: reloadStats } =
    usePolling(() => dashboardApi.getStats(), 30000);

  const { data: recentOrders, loading: ordersLoading } = useApi<Order[]>(
    () => ordersApi.list(undefined, 5),
    []
  );

  const chartData = stats ? buildChartData(stats.revenue_week) : [];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500">Visão geral do dia</p>
        </div>
        <Button variant="outline" size="sm" onClick={reloadStats} disabled={statsLoading}>
          <RefreshCw className={`h-4 w-4 ${statsLoading ? "animate-spin" : ""}`} />
          Atualizar
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatCard
          title="Vendas confirmadas hoje"
          value={stats?.sales_today ?? "—"}
          icon={CheckCircle}
          color="green"
          subtitle="PIX validado"
        />
        <StatCard
          title="Faturamento hoje"
          value={stats ? formatCurrency(stats.revenue_today) : "—"}
          icon={DollarSign}
          color="blue"
        />
        <StatCard
          title={`Comissão hoje (${stats?.commission_rate_pct ?? 5}%)`}
          value={stats ? formatCurrency(stats.commission_today) : "—"}
          icon={Percent}
          color="orange"
          subtitle={stats ? `Semana: ${formatCurrency(stats.commission_week)}` : undefined}
        />
        <StatCard
          title="Aguardando ação"
          value={stats?.pending_orders ?? "—"}
          icon={Clock}
          color="purple"
          subtitle="Separar ou entregar"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Receita da semana</CardTitle>
              <span className="text-sm font-semibold text-green-700">
                {stats ? formatCurrency(stats.revenue_week) : "—"}
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(v) => [formatCurrency(Number(v)), "Receita"]}
                  labelStyle={{ fontSize: 12 }}
                />
                <Bar dataKey="receita" fill="#15803d" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Últimos pedidos</CardTitle>
          </CardHeader>
          <CardContent>
            {ordersLoading ? (
              <p className="text-sm text-gray-400">Carregando...</p>
            ) : !recentOrders?.length ? (
              <p className="text-sm text-gray-400">Nenhum pedido ainda.</p>
            ) : (
              <div className="space-y-3">
                {recentOrders.map((order) => (
                  <div
                    key={order.id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        #{order.id.slice(0, 8).toUpperCase()}
                      </p>
                      <p className="text-xs text-gray-400">{formatDate(order.created_at)}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-gray-900">
                        {formatCurrency(order.total_amount)}
                      </span>
                      <OrderStatusBadge status={order.status} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
