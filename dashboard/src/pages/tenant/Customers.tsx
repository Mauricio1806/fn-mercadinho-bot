/**
 * Customers — lista de clientes do tenant com busca client-side e drawer de edição.
 *
 * Backend:
 * - GET /api/customers/?limit=&offset=
 * - GET /api/customers/{id}
 * - PATCH /api/customers/{id}
 */

import { useState, type ReactNode } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Users, X, Search, Ban, Save, ShieldCheck, Package } from "lucide-react";
import { getCustomers, getCustomer, updateCustomer } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { Skeleton } from "@/components/ui/Skeleton";
import type { Customer, CustomerUpdate } from "@/lib/types";

export function Customers() {
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: customers = [], isLoading } = useQuery({
    queryKey: ["customers"],
    queryFn: () => getCustomers({ limit: 500 }),
  });

  const filtered = customers.filter((c) => {
    if (!search.trim()) return true;
    const s = search.toLowerCase();
    return (
      c.phone.toLowerCase().includes(s) ||
      (c.name?.toLowerCase().includes(s) ?? false) ||
      (c.building_block?.toLowerCase().includes(s) ?? false) ||
      (c.apartment?.toLowerCase().includes(s) ?? false)
    );
  });

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Clientes</h1>
          <p className="page-subtitle">
            Quem já comprou pelo WhatsApp — histórico, endereço e bloqueios
          </p>
        </div>
      </div>

      <div style={{ marginTop: 12, position: "relative" }}>
        <Search
          size={14}
          style={{
            position: "absolute",
            left: 12,
            top: "50%",
            transform: "translateY(-50%)",
            color: "var(--color-text-muted)",
          }}
        />
        <input
          className="input"
          placeholder="Buscar por nome, telefone, bloco, apartamento..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ paddingLeft: 36 }}
        />
      </div>

      <div style={{ marginTop: 16 }}>
        {isLoading ? (
          <div className="card" style={{ padding: 24 }}>
            <Skeleton height={200} />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState hasSearch={!!search.trim()} />
        ) : (
          <CustomerTable customers={filtered} onClick={setSelectedId} />
        )}
      </div>

      {selectedId && (
        <CustomerDrawer
          customerId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      )}
    </>
  );
}

function CustomerTable({
  customers,
  onClick,
}: {
  customers: Customer[];
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
            <Th>Cliente</Th>
            <Th>Endereço</Th>
            <Th align="right">Pedidos</Th>
            <Th>Status</Th>
          </tr>
        </thead>
        <tbody>
          {customers.map((c) => (
            <tr
              key={c.id}
              onClick={() => onClick(c.id)}
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
                <div style={{ fontSize: 13, fontWeight: 500 }}>
                  {c.name ?? "(sem nome)"}
                </div>
                <div
                  style={{
                    fontSize: 11.5,
                    color: "var(--color-text-muted)",
                    marginTop: 2,
                    fontFamily: "monospace",
                  }}
                >
                  {c.phone}
                </div>
              </Td>
              <Td>
                {c.building_block || c.apartment ? (
                  <div style={{ fontSize: 12.5 }}>
                    {[c.building_block, c.apartment].filter(Boolean).join(" — ")}
                  </div>
                ) : (
                  <div style={{ fontSize: 12.5, color: "var(--color-text-muted)" }}>
                    —
                  </div>
                )}
              </Td>
              <Td align="right">
                <div style={{ fontWeight: 600 }}>{c.total_orders}</div>
              </Td>
              <Td>
                {c.is_blocked ? (
                  <span
                    style={{
                      fontSize: 11.5,
                      padding: "3px 8px",
                      borderRadius: 99,
                      background: "rgba(239,68,68,0.12)",
                      color: "rgb(239,68,68)",
                      fontWeight: 500,
                    }}
                  >
                    <Ban size={10} style={{ verticalAlign: "middle", marginRight: 4 }} />
                    Bloqueado
                  </span>
                ) : (
                  <span style={{ fontSize: 11.5, color: "var(--color-text-muted)" }}>
                    Ativo
                  </span>
                )}
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CustomerDrawer({
  customerId,
  onClose,
}: {
  customerId: string;
  onClose: () => void;
}) {
  const { data: customer, isLoading } = useQuery({
    queryKey: ["customer", customerId],
    queryFn: () => getCustomer(customerId),
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
          maxWidth: 480,
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
              {isLoading || !customer ? "Carregando..." : (customer.name ?? "Cliente sem nome")}
            </h2>
            {customer && (
              <div
                style={{
                  fontSize: 12,
                  color: "var(--color-text-muted)",
                  marginTop: 4,
                  fontFamily: "monospace",
                }}
              >
                {customer.phone}
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

        {isLoading || !customer ? (
          <Skeleton height={400} />
        ) : (
          <CustomerForm customer={customer} customerId={customerId} />
        )}
      </div>
    </>
  );
}

function CustomerForm({ customer, customerId }: { customer: Customer; customerId: string }) {
  const qc = useQueryClient();
  const [name, setName] = useState(customer.name ?? "");
  const [block, setBlock] = useState(customer.building_block ?? "");
  const [apt, setApt] = useState(customer.apartment ?? "");
  const [notes, setNotes] = useState(customer.notes ?? "");
  const [isBlocked, setIsBlocked] = useState(customer.is_blocked);

  const mut = useMutation({
    mutationFn: (body: CustomerUpdate) => updateCustomer(customerId, body),
    onSuccess: () => {
      toast.success("Cliente atualizado.");
      qc.invalidateQueries({ queryKey: ["customers"] });
      qc.invalidateQueries({ queryKey: ["customer", customerId] });
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Falhou ao salvar.");
    },
  });

  function save() {
    mut.mutate({
      name: name.trim() || null,
      building_block: block.trim() || null,
      apartment: apt.trim() || null,
      notes: notes.trim() || null,
      is_blocked: isBlocked,
    });
  }

  return (
    <>
      <Field label="Nome">
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
      </Field>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Field label="Bloco">
          <input className="input" value={block} onChange={(e) => setBlock(e.target.value)} />
        </Field>
        <Field label="Apartamento">
          <input className="input" value={apt} onChange={(e) => setApt(e.target.value)} />
        </Field>
      </div>

      <Field label="Notas internas" hint="Só você vê.">
        <textarea
          className="input"
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </Field>

      <Field label="Histórico">
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
          <Package size={14} color="var(--color-text-muted)" />
          {customer.total_orders} {customer.total_orders === 1 ? "pedido" : "pedidos"}
        </div>
      </Field>

      <div
        style={{
          padding: 12,
          background: isBlocked ? "rgba(239,68,68,0.10)" : "var(--color-surface-2)",
          borderRadius: 8,
          border: isBlocked ? "1px solid rgba(239,68,68,0.30)" : "1px solid transparent",
        }}
      >
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          <input
            type="checkbox"
            checked={isBlocked}
            onChange={(e) => setIsBlocked(e.target.checked)}
          />
          {isBlocked ? (
            <>
              <Ban size={14} color="rgb(239,68,68)" />
              <span>Cliente bloqueado — bot não responde mensagens dele</span>
            </>
          ) : (
            <>
              <ShieldCheck size={14} color="var(--color-text-muted)" />
              <span>Bloquear cliente (bot ignora mensagens)</span>
            </>
          )}
        </label>
      </div>

      <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
        Cliente desde {formatDateTime(customer.created_at)}
      </div>

      <button
        className="btn btn-primary"
        onClick={save}
        disabled={mut.isPending}
        style={{ marginTop: 8 }}
      >
        <Save size={14} />
        {mut.isPending ? "Salvando..." : "Salvar alterações"}
      </button>
    </>
  );
}

function EmptyState({ hasSearch }: { hasSearch: boolean }) {
  return (
    <div
      className="card"
      style={{ padding: 40, textAlign: "center", color: "var(--color-text-muted)" }}
    >
      <Users size={32} style={{ marginBottom: 12, opacity: 0.5 }} />
      <div>
        {hasSearch
          ? "Nenhum cliente bate com essa busca."
          : "Nenhum cliente cadastrado ainda."}
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

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <div
        style={{
          fontSize: 12,
          fontWeight: 500,
          color: "var(--color-text-muted)",
          marginBottom: 6,
        }}
      >
        {label}
      </div>
      {children}
      {hint && (
        <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 4 }}>
          {hint}
        </div>
      )}
    </div>
  );
}
