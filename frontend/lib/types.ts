// ── Auth ──────────────────────────────────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ── Orders ────────────────────────────────────────────────────────────────────
export type OrderStatus =
  | "pending"
  | "payment_confirmed"
  | "preparing"
  | "ready"
  | "delivering"
  | "delivered"
  | "cancelled";

export interface OrderItem {
  id: string;
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface Order {
  id: string;
  customer_id: string;
  status: OrderStatus;
  total_amount: number;
  delivery_building_block: string | null;
  delivery_apartment: string | null;
  delivery_fee: number;
  notes: string | null;
  pix_confirmed: boolean;
  commission_amount: number | null;
  items: OrderItem[];
  created_at: string;
  updated_at: string;
}

// ── Customers ─────────────────────────────────────────────────────────────────
export interface Customer {
  id: string;
  phone: string;
  name: string | null;
  building_block: string | null;
  apartment: string | null;
  is_blocked: boolean;
  total_orders: number;
  created_at: string;
}

// ── Products ──────────────────────────────────────────────────────────────────
export interface Product {
  id: string;
  name: string;
  description: string | null;
  price: number;
  category_id: string;
  stock_quantity: number | null;
  is_available: boolean;
  in_stock: boolean;
  created_at: string;
}

export interface ProductCategory {
  id: string;
  name: string;
  sort_order: number;
  is_active: boolean;
  products: Product[];
}

// ── Conversations ─────────────────────────────────────────────────────────────
export type ConversationStatus = "active" | "waiting" | "human" | "closed";
export type ConversationState =
  | "greeting"
  | "main_menu"
  | "order_items"
  | "order_confirm"
  | "order_delivery"
  | "order_payment"
  | "payment_receipt"
  | "delivery_info"
  | "hours_info"
  | "free_chat"
  | "closed";

export interface Conversation {
  id: string;
  customer_id: string;
  customer_phone: string | null;
  customer_name: string | null;
  status: ConversationStatus;
  state: ConversationState;
  message_count: number;
  last_message: string | null;
  created_at: string;
}

export type MessageDirection = "inbound" | "outbound";

export interface Message {
  id: string;
  direction: MessageDirection;
  content: string;
  is_ai_generated: boolean;
  tokens_used: number | null;
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export interface DashboardStats {
  orders_today: number;
  sales_today: number;
  revenue_today: number;
  commission_today: number;
  revenue_week: number;
  commission_week: number;
  total_customers: number;
  pending_orders: number;
  commission_rate_pct: number;
}

// ── UI ────────────────────────────────────────────────────────────────────────
export const ORDER_STATUS_LABEL: Record<OrderStatus, string> = {
  pending: "Aguard. comprovante",
  payment_confirmed: "PIX confirmado",
  preparing: "Preparando",
  ready: "Pronto",
  delivering: "Saiu p/ entrega",
  delivered: "Entregue",
  cancelled: "Cancelado",
};

export const ORDER_STATUS_COLOR: Record<OrderStatus, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  payment_confirmed: "bg-green-100 text-green-800",
  preparing: "bg-purple-100 text-purple-800",
  ready: "bg-cyan-100 text-cyan-800",
  delivering: "bg-orange-100 text-orange-800",
  delivered: "bg-emerald-100 text-emerald-800",
  cancelled: "bg-red-100 text-red-800",
};
