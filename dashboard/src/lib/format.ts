/**
 * Helpers de formatação — usados em todas as páginas.
 */

import type { OrderStatus } from "./types";

export function formatBRL(value: number): string {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
  });
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const STATUS_LABEL: Record<OrderStatus, string> = {
  pending: "Aguardando",
  payment_confirmed: "Pago",
  preparing: "Preparando",
  ready: "Pronto",
  delivering: "Saiu p/ entrega",
  delivered: "Entregue",
  cancelled: "Cancelado",
};
