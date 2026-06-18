/**
 * Tipos centralizados do domínio Atendê.
 */

export type OrderStatus =
  | "pending"
  | "payment_confirmed"
  | "preparing"
  | "ready"
  | "delivering"
  | "delivered"
  | "cancelled";

export interface DashboardStats {
  orders_today: number;
  sales_today: number;
  revenue_today: number;
  commission_today: number;
  revenue_week: number;
  commission_week: number;
  total_customers: number;
  pending_orders: number;
}

export interface ConsolidatedStats {
  total_tenants_active: number;
  revenue_today_all: number;
  commission_today_all: number;
  revenue_week_all: number;
  commission_week_all: number;
  total_orders_platform: number;
}

export interface SalesItem {
  nome: string;
  qty: number;
  subtotal: number;
}

export interface SalesEntry {
  id: string;
  created_at: string;
  customer: string;
  items: SalesItem[];
  total: number;
  delivery_fee: number;
  commission: number;
  status: OrderStatus;
  tenant_id: string;
}

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
  items: OrderItem[];
  created_at: string;
  updated_at: string;
}

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
  external_source?: string | null;
}

export type IntegrationSystem = "bling" | "tiny" | "webhook" | null;

export interface IntegrationConfig {
  sistema: IntegrationSystem;
  ativo: boolean;
  api_key_set: boolean;
  api_key_preview?: string;
  sync_intervalo_minutos?: number;
  client_id?: string;
}

export interface SyncResult {
  status: string;
  created: number;
  updated: number;
  total_processed?: number;
  errors: string[];
}
