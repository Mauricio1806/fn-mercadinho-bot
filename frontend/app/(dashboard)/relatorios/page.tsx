"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { RefreshCw, TrendingUp } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { ordersApi, customersApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { Order } from "@/lib/types";
import { ORDER_STATUS_LABEL, ORDER_STATUS_COLOR } from "@/lib/types";

// Statuses que representam venda efetivada (PIX confirmado)
const CONFIRMED_STATUSES = new Set(["payment_confirmed", "preparing", "ready", "delivering", "delivered"]);

const STATUS_CHART_COLORS: Record<string, string> = {
  pending: "#f59e0b",
  payment_confirmed: "#22c55e",
  preparing: "#8b5cf6",
  ready: "#06b6d4",
  delivering: "#f97316",
  delivered: "#10b981",
  cancelled: "#ef4444",
};

export default function RelatoriosPage() {
  const { data: orders, loading: ordersLoading, reload } = useApi<Order[]>(
    () => ordersApi.list(undefined, 200),
    []
  );

  const { data: customers, loading: customersLoading } = useApi(
    () => customersApi.list(200),
    []
  );

  const loading = ordersLoading || customersLoading;

  // --- Derived stats ---
  // Receita = apenas vendas com PIX confirmado
  const confirmedOrders = orders?.filter((o) => CONFIRMED_STATUSES.has(o.status)) ?? [];

  const totalRevenue = confirmedOrders.reduce((sum, o) => sum + o.total_amount, 0);
  const totalCommission = confirmedOrders.reduce((sum, o) => sum + (o.commission_amount ?? 0), 0);
  const avgTicket = confirmedOrders.length > 0 ? totalRevenue / confirmedOrders.length : 0;

  // Status breakdown for pie chart
  const statusCounts = orders?.reduce<Record<string, number>>((acc, o) => {
    acc[o.status] = (acc[o.status] ?? 0) + 1;
    return acc;
  }, {});

  const pieData = Object.entries(statusCounts ?? {}).map(([status, count]) => ({
    name: ORDER_STATUS_LABEL[status as keyof typeof ORDER_STATUS_LABEL] ?? status,
    value: count,
    color: STATUS_CHART_COLORS[status] ?? "#6b7280",
  }));

  // Revenue by day (last 7 days)
  const dayRevenue: Record<string, number> = {};
  const dayLabels: string[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    const label = d.toLocaleDateString("pt-BR", { weekday: "short" });
    dayRevenue[key] = 0;
    dayLabels.push(label);
  }

  confirmedOrders.forEach((o) => {
      const key = o.created_at.slice(0, 10);
      if (key in dayRevenue) dayRevenue[key] += o.total_amount;
    });

  const revenueChartData = Object.entries(dayRevenue).map(([, amount], i) => ({
    day: dayLabels[i],
    receita: Math.round(amount * 100) / 100,
  }));

  // Top products (só vendas confirmadas)
  const productSales: Record<string, { name: string; qty: number; revenue: number }> = {};
  confirmedOrders.forEach((o) => {
      o.items.forEach((item) => {
        if (!productSales[item.product_id]) {
          productSales[item.product_id] = { name: item.product_name, qty: 0, revenue: 0 };
        }
        productSales[item.product_id].qty += item.quantity;
        productSales[item.product_id].revenue += item.subtotal;
      });
    });

  const topProducts = Object.values(productSales)
    .sort((a, b) => b.qty - a.qty)
    .slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Relatórios</h1>
          <p className="text-sm text-gray-500">Baseado nos últimos 200 pedidos</p>
        </div>
        <Button variant="outline" size="sm" onClick={reload} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">Calculando relatórios...</p>
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            <Card>
              <CardContent className="p-5">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Faturamento (vendas confirmadas)</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{formatCurrency(totalRevenue)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Comissão gerada</p>
                <p className="mt-1 text-2xl font-bold text-green-700">{formatCurrency(totalCommission)}</p>
                <p className="text-xs text-gray-400 mt-0.5">{confirmedOrders.length} vendas confirmadas</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Ticket médio</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{formatCurrency(avgTicket)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Total de clientes</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{(customers as unknown[])?.length ?? 0}</p>
              </CardContent>
            </Card>
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            {/* Revenue last 7 days */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-green-700" />
                  <CardTitle className="text-base">Receita — últimos 7 dias</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart
                    data={revenueChartData}
                    margin={{ top: 0, right: 0, left: -20, bottom: 0 }}
                  >
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

            {/* Orders by status (pie) */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Pedidos por status</CardTitle>
              </CardHeader>
              <CardContent>
                {pieData.length === 0 ? (
                  <p className="text-sm text-gray-400">Sem dados.</p>
                ) : (
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={pieData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={70}
                        label={({ name, percent }) =>
                          `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                        }
                        labelLine={false}
                      >
                        {pieData.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Pie>
                      <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Top products table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Produtos mais vendidos</CardTitle>
            </CardHeader>
            <CardContent>
              {topProducts.length === 0 ? (
                <p className="text-sm text-gray-400">Sem dados de vendas.</p>
              ) : (
                <div className="divide-y">
                  {topProducts.map((p, i) => (
                    <div key={i} className="flex items-center justify-between py-2.5">
                      <div className="flex items-center gap-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-100 text-xs font-bold text-green-700">
                          {i + 1}
                        </span>
                        <span className="text-sm font-medium text-gray-900">{p.name}</span>
                      </div>
                      <div className="flex items-center gap-6 text-sm text-gray-500">
                        <span>{p.qty} un.</span>
                        <span className="font-semibold text-gray-900">
                          {formatCurrency(p.revenue)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
