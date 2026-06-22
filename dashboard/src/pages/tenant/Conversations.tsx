/**
 * Conversations — lista de threads WhatsApp + drawer com mensagens + takeover.
 *
 * Backend:
 * - GET /api/conversations/?status_filter=&limit=
 * - GET /api/conversations/{id}/messages
 * - POST /api/conversations/{id}/takeover
 */

import { useState, type ReactNode } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { MessageCircle, User, X, Hand, ChevronRight, Sparkles } from "lucide-react";
import {
  getConversations,
  getConversationMessages,
  takeoverConversation,
} from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { Skeleton } from "@/components/ui/Skeleton";
import type {
  Conversation,
  ConversationStatus,
  ConversationState,
  Message,
} from "@/lib/types";

const STATUS_FILTERS: { value: ConversationStatus | "all"; label: string }[] = [
  { value: "all", label: "Todas" },
  { value: "active", label: "Ativas" },
  { value: "waiting", label: "Aguardando" },
  { value: "human", label: "Atendente humano" },
  { value: "closed", label: "Encerradas" },
];

const STATUS_LABEL: Record<ConversationStatus, string> = {
  active: "Ativa",
  waiting: "Aguardando",
  human: "Humano",
  closed: "Encerrada",
};

const STATE_LABEL: Record<ConversationState, string> = {
  greeting: "Saudação",
  main_menu: "Menu",
  order_items: "Montando pedido",
  order_confirm: "Confirmando",
  order_delivery: "Entrega",
  order_payment: "Pagamento",
  payment_receipt: "Aguarda comprovante",
  delivery_info: "Info entrega",
  hours_info: "Info horário",
  free_chat: "Livre",
  closed: "Fechada",
};

export function Conversations() {
  const [filter, setFilter] = useState<ConversationStatus | "all">("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: conversations = [], isLoading } = useQuery({
    queryKey: ["conversations", filter],
    queryFn: () =>
      getConversations(
        filter === "all" ? { limit: 100 } : { status_filter: filter, limit: 100 },
      ),
  });

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Conversas</h1>
          <p className="page-subtitle">
            Atendimentos do bot via WhatsApp — você pode assumir qualquer conversa
          </p>
        </div>
      </div>

      <FilterChips active={filter} onChange={setFilter} />

      <div style={{ marginTop: 16 }}>
        {isLoading ? (
          <div className="card" style={{ padding: 24 }}>
            <Skeleton height={200} />
          </div>
        ) : conversations.length === 0 ? (
          <EmptyState />
        ) : (
          <ConversationList conversations={conversations} onClick={setSelectedId} />
        )}
      </div>

      {selectedId && (
        <ConversationDrawer
          conversationId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      )}
    </>
  );
}

function FilterChips({
  active,
  onChange,
}: {
  active: ConversationStatus | "all";
  onChange: (v: ConversationStatus | "all") => void;
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

function ConversationList({
  conversations,
  onClick,
}: {
  conversations: Conversation[];
  onClick: (id: string) => void;
}) {
  return (
    <div className="card" style={{ overflow: "hidden" }}>
      {conversations.map((c, idx) => (
        <div
          key={c.id}
          onClick={() => onClick(c.id)}
          style={{
            cursor: "pointer",
            padding: "14px 16px",
            borderBottom:
              idx < conversations.length - 1 ? "1px solid var(--color-border)" : "none",
            display: "flex",
            alignItems: "center",
            gap: 12,
            transition: "background 150ms",
          }}
          onMouseEnter={(e) =>
            (e.currentTarget.style.background = "var(--color-surface-2)")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.background = "transparent")
          }
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              background:
                c.status === "human"
                  ? "rgba(245,158,11,0.15)"
                  : "var(--color-surface-2)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            {c.status === "human" ? (
              <Hand size={16} color="rgb(245,158,11)" />
            ) : (
              <User size={16} />
            )}
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 8,
              }}
            >
              <div style={{ fontWeight: 500, fontSize: 13.5 }}>
                {c.customer_name ?? c.customer_phone ?? "Cliente"}
              </div>
              <div style={{ fontSize: 11, color: "var(--color-text-muted)", flexShrink: 0 }}>
                {formatDateTime(c.created_at)}
              </div>
            </div>

            <div
              style={{
                fontSize: 12.5,
                color: "var(--color-text-muted)",
                marginTop: 4,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {c.last_message ?? "(sem mensagens)"}
            </div>

            <div style={{ marginTop: 6, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <Chip color={statusColor(c.status)}>{STATUS_LABEL[c.status]}</Chip>
              <Chip>{STATE_LABEL[c.state] ?? c.state}</Chip>
              <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
                {c.message_count} {c.message_count === 1 ? "msg" : "msgs"}
              </span>
            </div>
          </div>

          <ChevronRight size={16} color="var(--color-text-muted)" />
        </div>
      ))}
    </div>
  );
}

function ConversationDrawer({
  conversationId,
  onClose,
}: {
  conversationId: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { data: messages = [], isLoading } = useQuery({
    queryKey: ["conversation-messages", conversationId],
    queryFn: () => getConversationMessages(conversationId),
  });

  const takeover = useMutation({
    mutationFn: () => takeoverConversation(conversationId),
    onSuccess: () => {
      toast.success("Você assumiu a conversa. Bot pausado.");
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Falhou ao assumir.");
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
          maxWidth: 540,
          background: "var(--color-surface)",
          borderLeft: "1px solid var(--color-border)",
          zIndex: 101,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid var(--color-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>
            Histórico da conversa
          </h2>
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

        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "16px 20px",
            display: "flex",
            flexDirection: "column",
            gap: 10,
            background: "var(--color-surface-2)",
          }}
        >
          {isLoading ? (
            <Skeleton height={400} />
          ) : messages.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                color: "var(--color-text-muted)",
                fontSize: 13,
                padding: 20,
              }}
            >
              Nenhuma mensagem nessa conversa.
            </div>
          ) : (
            messages.map((m) => <MessageBubble key={m.id} message={m} />)
          )}
        </div>

        <div
          style={{
            padding: "12px 20px",
            borderTop: "1px solid var(--color-border)",
            background: "var(--color-surface)",
          }}
        >
          <button
            className="btn btn-ghost"
            onClick={() => takeover.mutate()}
            disabled={takeover.isPending}
            style={{ width: "100%" }}
          >
            <Hand size={14} />
            {takeover.isPending ? "Pausando bot..." : "Assumir conversa (pausa o bot)"}
          </button>
          <p
            style={{
              fontSize: 11,
              color: "var(--color-text-muted)",
              marginTop: 8,
              textAlign: "center",
            }}
          >
            A resposta humana via WhatsApp acontece fora dessa interface.
          </p>
        </div>
      </div>
    </>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isInbound = message.direction === "inbound";
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: isInbound ? "flex-start" : "flex-end",
      }}
    >
      <div
        style={{
          maxWidth: "75%",
          padding: "8px 12px",
          borderRadius: 12,
          fontSize: 13,
          background: isInbound ? "var(--color-surface)" : "var(--color-primary-light)",
          color: isInbound ? "var(--color-text)" : "var(--color-primary)",
          border: "1px solid var(--color-border)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {message.content}
      </div>
      <div
        style={{
          fontSize: 10.5,
          color: "var(--color-text-muted)",
          marginTop: 3,
          display: "flex",
          gap: 6,
          alignItems: "center",
        }}
      >
        {message.is_ai_generated && (
          <>
            <Sparkles size={9} />
            <span>IA</span>
            <span>·</span>
          </>
        )}
        {message.created_at ? formatDateTime(message.created_at) : ""}
      </div>
    </div>
  );
}

function Chip({ children, color }: { children: ReactNode; color?: string }) {
  return (
    <span
      style={{
        fontSize: 10.5,
        padding: "2px 8px",
        borderRadius: 99,
        background: color ? `${color}1A` : "var(--color-surface-2)",
        color: color ?? "var(--color-text-muted)",
        fontWeight: 500,
        border: "1px solid var(--color-border)",
      }}
    >
      {children}
    </span>
  );
}

function statusColor(s: ConversationStatus): string {
  switch (s) {
    case "active":
      return "rgb(34,197,94)";
    case "waiting":
      return "rgb(245,158,11)";
    case "human":
      return "rgb(99,102,241)";
    case "closed":
    default:
      return "rgb(148,163,184)";
  }
}

function EmptyState() {
  return (
    <div
      className="card"
      style={{ padding: 40, textAlign: "center", color: "var(--color-text-muted)" }}
    >
      <MessageCircle size={32} style={{ marginBottom: 12, opacity: 0.5 }} />
      <div>Nenhuma conversa registrada ainda.</div>
    </div>
  );
}
