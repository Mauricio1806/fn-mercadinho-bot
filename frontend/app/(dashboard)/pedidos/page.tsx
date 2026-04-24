"use client";

import { useState } from "react";
import { RefreshCw, MapPin, Package } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { ordersApi } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import type { Order, OrderStatus } from "@/lib/types";
import { ORDER_STATUS_LABEL } from "@/lib/types";

const STATUSES: OrderStatus[] = [
  "pending", "payment_confirmed", "preparing", "ready", "delivering", "delivered", "cancelled",
];

const NEXT_STATUS: Partial<Record<OrderStatus, OrderStatus>> = {
  pending: "payment_confirmed",
  payment_confirmed: "preparing",
  preparing: "ready",
  ready: "delivering",
  delivering: "delivered",
};

export default function PedidosPage() {
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "all">("all");
  const [updating, setUpdating] = useState<string | null>(null);

  const { data: orders, loading, reload } = useApi<Order[]>(
    () => ordersApi.list(statusFilter === "all" ? undefined : statusFilter, 100),
    [statusFilter]
  );

  async function advanceStatus(order: Order) {
    const next = NEXT_STATUS[order.status];
    if (!next) return;
    setUpdating(order.id);
    try {
      await ordersApi.updateStatus(order.id, next);
      reload();
    } finally {
      setUpdating(null);
    }
  }

  async function cancelOrder(order: Order) {
    if (!confirm("Cancelar este pedido?")) return;
    setUpdating(order.id);
    try {
      await ordersApi.updateStatus(order.id, "cancelled");
      reload();
    } finally {
      setUpdating(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pedidos</h1>
          <p className="text-sm text-gray-500">{orders?.length ?? 0} pedido(s)</p>
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={statusFilter}
            onValueChange={(v) => setStatusFilter(v as OrderStatus | "all")}
          >
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Filtrar por status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              {STATUSES.map((s) => (
                <SelectItem key={s} value={s}>{ORDER_STATUS_LABEL[s]}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={reload} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Orders list */}
      {loading ? (
        <p className="text-sm text-gray-400">Carregando pedidos...</p>
      ) : orders?.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-gray-400">
            <Package className="mx-auto mb-3 h-10 w-10 opacity-30" />
            <p>Nenhum pedido encontrado.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {orders?.map((order) => (
            <Card key={order.id}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-4">
                  {/* Order info */}
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-sm font-semibold text-gray-900">
                        #{order.id.slice(0, 8).toUpperCase()}
                      </span>
                      <OrderStatusBadge status={order.status} />
                    </div>

                    {/* Items */}
                    <div className="space-y-0.5">
                      {order.items.map((item) => (
                        <p key={item.id} className="text-sm text-gray-600">
                          {item.product_name} ×{item.quantity} —{" "}
                          <span className="text-gray-800">{formatCurrency(item.subtotal)}</span>
                        </p>
                      ))}
                    </div>

                    {/* Delivery */}
                    {order.delivery_building_block && (
                      <p className="flex items-center gap-1 text-xs text-gray-500">
                        <MapPin className="h-3.5 w-3.5" />
                        Bloco {order.delivery_building_block}, Apto {order.delivery_apartment}
                      </p>
                    )}

                    <p className="text-xs text-gray-400">{formatDate(order.created_at)}</p>
                  </div>

                  {/* Right: total + actions */}
                  <div className="flex flex-col items-end gap-3">
                    <p className="text-lg font-bold text-gray-900">
                      {formatCurrency(order.total_amount)}
                    </p>

                    <div className="flex gap-2">
                      {NEXT_STATUS[order.status] && (
                        <Button
                          size="sm"
                          onClick={() => advanceStatus(order)}
                          disabled={updating === order.id}
                        >
                          {ORDER_STATUS_LABEL[NEXT_STATUS[order.status]!]}
                        </Button>
                      )}
                      {order.status !== "delivered" && order.status !== "cancelled" && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-red-600 hover:border-red-300 hover:bg-red-50"
                          onClick={() => cancelOrder(order)}
                          disabled={updating === order.id}
                        >
                          Cancelar
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
