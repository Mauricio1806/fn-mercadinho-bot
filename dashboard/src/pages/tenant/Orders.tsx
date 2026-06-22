/**
 * Orders — lista de pedidos com filtro de status e drawer de detalhe.
 *
 * Backend:
 * - GET /api/orders/?status_filter=&limit=
 * - GET /api/orders/{id}
 * - PATCH /api/orders/{id}/status  (dispara notificação WhatsApp ao cliente)
 */

import { useState, type ReactNode } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  Package,
  MapPin,
  X,
  RefreshCw,
  ChevronRight,
} from "lucide-react";
import { getOrders, getOrder, updateOrderStatus } from "@/lib/api";
import { formatBRL, formatDateTime, STATUS_LABEL } from "@/lib/format";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import type { Order, OrderStatus } from "@/lib/types";

const STATUS_FILTERS: { value: OrderStatus | "all"; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "pending", label: "Aguardando" },
  { value: "payment_confirmed", label: "Pago" },
  { value: "preparing", label: "Preparando" },
  { value: "ready", label: "Pronto" },
  { value: "delivering", label: "Em rota" },
  { value: "delivered", label: "Entregue" },
  { value: "cancelled", label: "Cancelado" },
];

export function Orders() {
  const [filter, setFilter] = useState<OrderStatus | "all">("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: orders = [], isLoading, refetch } = useQuery({
    queryKey: ["orders", filter],
    queryFn: () =>
      getOrders(
        filter === "all" ? { limit: 100 } : { status_filter: filter, limit: 100 },
      ),
  });

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Pedidos</h1>
          <p className="page-subtitle">
            Pedidos recebidos via WhatsApp e seu status atual
          </p>
        </div>
        <button className="btn btn-ghost" onClick={() => refetch()}>
          <RefreshCw size={14} /> Atualizar
        </button>
      </div>

      <FilterChips active={filter} onChange={setFilter} />

      <div style={{ marginTop: 16 }}>
        {isLoading ? (
          <div className="card" style={{ padding: 24 }}>
            <Skeleton height={200} />
          </div>
        ) : orders.length === 0 ? (
          <EmptyState filter={filter} />
        ) : (
          <OrderTable orders={orders} onClick={setSelectedId} />
        )}
      </div>

      {selectedId && (
        <OrderDrawer orderId={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </>
  );
}

function FilterChips({
  active,
  onChange,
}: {
  active: OrderStatus | "all";
  onChange: (v: OrderStatus | "all") => void;
}) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
      {STATUS_FILTERS.map((f) => {
        const isActive = active === f.value;
        return (
          <button
            key={f.value}
            onClick={() => onChange(f.value)}
            style={{
              padding: "6px 14px",
              borderRadius: 99,
              fontSize: 12.5,
              fontWeight: 500,
              border: isActive
                ? "1px solid var(--color-primary)"
                : "1px solid var(--color-border)",
              background: isActive
                ? "var(--color-primary-light)"
                : "transparent",
              color: isActive ? "var(--color-primary)" : "var(--color-text)",
              cursor: "pointer",
              transition: "all 200ms",
            }}
          >
            {f.label}
          </button>
        );
      })}
    </div>
  );
}

function OrderTable({
  orders,
  onClick,
}: {
  orders: Order[];
  onClick: (id: string) => void;
}) {
  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr
            style={{
              background: "var(--color-surface-2)",
              borderBottom: "1px solid var(--color-border)",
            }}
          >
            <Th>Quando</Th>
            <Th>Itens</Th>
            <Th>Endereço</Th>
            <Th align="right">Total</Th>
            <Th>Status</Th>
            <Th />
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr
              key={o.id}
              onClick={() => onClick(o.id)}
              style={{
                cursor: "pointer",
                borderBottom: "1px solid var(--color-border)",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "var(--color-surface-2)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "transparent")
              }
            >
              <Td>
                <div style={{ fontSize: 12.5 }}>{formatDateTime(o.created_at)}</div>
              </Td>
              <Td>
                <div style={{ fontSize: 13 }}>
                  {o.items.length} {o.items.length === 1 ? "item" : "itens"}
                </div>
                <div
                  style={{
                    fontSize: 11.5,
                    color: "var(--color-text-muted)",
                    marginTop: 2,
                  }}
                >
                  {o.items
                    .slice(0, 2)
                    .map((i) => `${i.quantity}× ${i.product_name}`)
                    .join(", ")}
                  {o.items.length > 2 && ` +${o.items.length - 2}`}
                </div>
              </Td>
              <Td>
                <div style={{ fontSize: 12.5 }}>
                  {o.delivery_building_block || o.delivery_apartment
                    ? `${o.delivery_building_block ?? ""} ${o.delivery_apartment ?? ""}`.trim()
                    : "—"}
                </div>
              </Td>
              <Td align="right">
                <div style={{ fontWeight: 600 }}>{formatBRL(o.total_amount)}</div>
                {o.delivery_fee > 0 && (
                  <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
                    inclui {formatBRL(o.delivery_fee)} frete
                  </div>
                )}
              </Td>
              <Td>
                <StatusBadge status={o.status} />
              </Td>
              <Td>
                <ChevronRight size={16} color="var(--color-text-muted)" />
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OrderDrawer({
  orderId,
  onClose,
}: {
  orderId: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { data: order, isLoading } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => getOrder(orderId),
  });

  const mut = useMutation({
    mutationFn: (status: OrderStatus) => updateOrderStatus(orderId, status),
    onSuccess: () => {
      toast.success("Status atualizado. WhatsApp disparado.");
      qc.invalidateQueries({ queryKey: ["orders"] });
      qc.invalidateQueries({ queryKey: ["order", orderId] });
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Falhou ao atualizar.");
    },
  });

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.5)",
          zIndex: 100,
        }}
      />
      <div
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          width: "100%",
          maxWidth: 520,
          background: "var(--color-surface)",
          borderLeft: "1px solid var(--color-border)",
          zIndex: 101,
          overflowY: "auto",
          padding: 24,
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
              {isLoading || !order ? "Carregando..." : `Pedido #${order.id.slice(0, 8)}`}
            </h2>
            {order && (
              <div
                style={{
                  fontSize: 12,
                  color: "var(--color-text-muted)",
                  marginTop: 4,
                }}
              >
                {formatDateTime(order.created_at)}
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: 4,
              color: "var(--color-text-muted)",
            }}
          >
            <X size={18} />
          </button>
        </div>

        {isLoading || !order ? (
          <Skeleton height={400} />
        ) : (
          <>
            <div>
              <Label>Status atual</Label>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <StatusBadge status={order.status} />
                <select
                  className="input"
                  value={order.status}
                  onChange={(e) => mut.mutate(e.target.value as OrderStatus)}
                  disabled={mut.isPending}
                  style={{ flex: 1 }}
                >
                  {(Object.keys(STATUS_LABEL) as OrderStatus[]).map((s) => (
                    <option key={s} value={s}>
                      Mudar para: {STATUS_LABEL[s]}
                    </option>
                  ))}
                </select>
              </div>
              <p
                style={{
                  fontSize: 11.5,
                  color: "var(--color-text-muted)",
                  marginTop: 6,
                }}
              >
                Mudar o status dispara notificação WhatsApp pro cliente.
              </p>
            </div>

            <div>
              <Label>Itens ({order.items.length})</Label>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {order.items.map((i) => (
                  <div
                    key={i.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      padding: "10px 12px",
                      background: "var(--color-surface-2)",
                      borderRadius: 8,
                      fontSize: 13,
                    }}
                  >
                    <div>
                      <div>{i.product_name}</div>
                      <div
                        style={{
                          fontSize: 11.5,
                          color: "var(--color-text-muted)",
                          marginTop: 2,
                        }}
                      >
                        {i.quantity} × {formatBRL(i.unit_price)}
                      </div>
                    </div>
                    <div style={{ fontWeight: 600 }}>{formatBRL(i.subtotal)}</div>
                  </div>
                ))}
              </div>
            </div>

            <div
              style={{
                padding: 12,
                background: "var(--color-surface-2)",
                borderRadius: 8,
                fontSize: 13,
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}
            >
              <Row
                label="Subtotal"
                value={formatBRL(order.total_amount - order.delivery_fee)}
              />
              {order.delivery_fee > 0 && (
                <Row label="Entrega" value={formatBRL(order.delivery_fee)} />
              )}
              <Row label="Total" value={formatBRL(order.total_amount)} bold />
            </div>

            {(order.delivery_building_block || order.delivery_apartment) && (
              <div>
                <Label>
                  <MapPin size={12} style={{ verticalAlign: "middle" }} /> Endereço
                </Label>
                <div style={{ fontSize: 13 }}>
                  {[order.delivery_building_block, order.delivery_apartment]
                    .filter(Boolean)
                    .join(" — ")}
                </div>
              </div>
            )}

            {order.notes && (
              <div>
                <Label>Observações</Label>
                <div
                  style={{
                    fontSize: 13,
                    padding: 12,
                    background: "var(--color-surface-2)",
                    borderRadius: 8,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {order.notes}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}

function EmptyState({ filter }: { filter: OrderStatus | "all" }) {
  return (
    <div
      className="card"
      style={{
        padding: 40,
        textAlign: "center",
        color: "var(--color-text-muted)",
      }}
    >
      <Package size={32} style={{ marginBottom: 12, opacity: 0.5 }} />
      <div>
        Nenhum pedido
        {filter === "all"
          ? " registrado."
          : ` com status "${STATUS_LABEL[filter as OrderStatus]}".`}
      </div>
    </div>
  );
}

function Th({ children, align = "left" }: { children?: ReactNode; align?: "left" | "right" }) {
  return (
    <th
      style={{
        textAlign: align,
        padding: "12px 16px",
        fontSize: 11,
        fontWeight: 500,
        color: "var(--color-text-muted)",
        textTransform: "uppercase",
        letterSpacing: 0.5,
      }}
    >
      {children}
    </th>
  );
}

function Td({ children, align = "left" }: { children?: ReactNode; align?: "left" | "right" }) {
  return (
    <td
      style={{ padding: "12px 16px", fontSize: 13, textAlign: align, verticalAlign: "top" }}
    >
      {children}
    </td>
  );
}

function Label({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        fontSize: 12,
        color: "var(--color-text-muted)",
        marginBottom: 6,
        textTransform: "uppercase",
        letterSpacing: 0.5,
      }}
    >
      {children}
    </div>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontWeight: bold ? 600 : 400 }}>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}
