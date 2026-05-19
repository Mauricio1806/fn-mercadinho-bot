/**
 * Página de pedidos com troca de status e notificação automática ao cliente.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getOrders, updateOrderStatus } from "@/lib/api";
import toast from "react-hot-toast";

const STATUSES = [
  { value: "pending", label: "Aguardando PIX" },
  { value: "payment_confirmed", label: "PIX Confirmado" },
  { value: "preparing", label: "Preparando" },
  { value: "ready", label: "Pronto" },
  { value: "delivering", label: "Em Entrega" },
  { value: "delivered", label: "Entregue" },
  { value: "cancelled", label: "Cancelado" },
];

export function Orders() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<string>("");

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["orders", filter],
    queryFn: () => getOrders(filter ? { status_filter: filter } : {}),
    refetchInterval: 15_000,
  });

  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      updateOrderStatus(id, status),
    onSuccess: (_, { status }) => {
      toast.success(`Status atualizado → ${STATUSES.find(s => s.value === status)?.label}`);
      qc.invalidateQueries({ queryKey: ["orders"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
    onError: () => toast.error("Falhou ao atualizar status."),
  });

  const fmtCurrency = (n: number) =>
    n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Pedidos</h1>
          <p className="page-subtitle">Gerencie e atualize o status de cada pedido</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <select
            id="order-status-filter"
            className="input"
            style={{ width: "auto" }}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="">Todos os status</option>
            {STATUSES.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrapper" style={{ border: "none", borderRadius: "14px" }}>
          <table>
            <thead>
              <tr>
                <th>Pedido</th>
                <th>Cliente</th>
                <th>Itens</th>
                <th>Total</th>
                <th>Delivery</th>
                <th>Status Atual</th>
                <th>Ação</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={7} style={{ textAlign: "center", padding: 32, color: "var(--color-text-muted)" }}>Carregando...</td></tr>
              ) : !orders.length ? (
                <tr><td colSpan={7} style={{ textAlign: "center", padding: 32, color: "var(--color-text-muted)" }}>Nenhum pedido encontrado</td></tr>
              ) : (
                orders.map((order: any) => (
                  <tr key={order.id}>
                    <td style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 600 }}>
                      #{String(order.id).slice(0, 8).toUpperCase()}
                    </td>
                    <td style={{ fontSize: 12 }}>
                      {String(order.customer_id).slice(0, 8)}
                    </td>
                    <td>
                      {(order.items ?? []).map((item: any) => (
                        <div key={item.id} style={{ fontSize: 12 }}>
                          {item.quantity}× {item.product_name}
                        </div>
                      ))}
                    </td>
                    <td style={{ fontWeight: 600 }}>{fmtCurrency(order.total_amount)}</td>
                    <td style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                      {order.delivery_building_block ? `Bloco ${order.delivery_building_block}` : "Retirada"}
                    </td>
                    <td>
                      <span className={`badge badge-${order.status}`}>
                        {STATUSES.find(s => s.value === order.status)?.label ?? order.status}
                      </span>
                    </td>
                    <td>
                      <select
                        id={`status-select-${order.id}`}
                        className="input"
                        style={{ width: "auto", fontSize: 12, padding: "6px 10px" }}
                        value={order.status}
                        onChange={(e) =>
                          mutation.mutate({ id: order.id, status: e.target.value })
                        }
                        disabled={mutation.isPending}
                      >
                        {STATUSES.map(s => (
                          <option key={s.value} value={s.value}>{s.label}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
