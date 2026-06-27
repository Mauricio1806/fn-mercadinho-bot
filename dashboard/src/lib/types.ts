/**
 * Tipos centralizados do domínio Mercazap.
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


export interface TenantHorario {
  abertura?: string;
  fechamento?: string;
  domingo_abertura?: string;
  domingo_fechamento?: string;
  dias?: string;
  msg_fora_horario?: string;
}

export interface TenantDelivery {
  taxa_proxima?: number;
  taxa_distante?: number;
  raio_proxima_metros?: number;
  pedido_minimo?: number;
  tempo_estimado?: string;
}

export interface TenantPersona {
  tom?: "formal" | "informal";
  usa_emojis?: boolean;
  saudacao?: string;
  despedida?: string;
  tratamento?: "você" | "senhor" | string;
}

export interface TenantBranding {
  cor_primaria?: string;
  cor_secundaria?: string;
  logo_url?: string | null;
}

export interface TenantConfig {
  endereco?: string;
  pix_chave?: string;
  pix_tipo_chave?: "cnpj" | "cpf" | "email" | "telefone" | "aleatoria" | string;
  pix_titular?: string;
  pix_banco?: string;
  owners?: string[];
  horario?: TenantHorario;
  delivery?: TenantDelivery;
  persona?: TenantPersona;
  branding?: TenantBranding;
  integracao_estoque?: IntegrationConfig;
  [key: string]: unknown;
}

export interface MyTenant {
  id: string;
  slug: string;
  name: string;
  whatsapp_number: string | null;
  config: TenantConfig;
}


export interface TenantSummary {
  id: string;
  slug: string;
  name: string;
  whatsapp_number: string | null;
  is_active: boolean;
  created_at?: string;
}

// ── Customers ──────────────────────────────────────────────────────────

export interface Customer {
  id: string;
  tenant_id?: string;
  phone: string;
  name: string | null;
  building_block: string | null;
  apartment: string | null;
  notes: string | null;
  is_blocked: boolean;
  total_orders: number;
  created_at: string;
  updated_at?: string;
}

export interface CustomerUpdate {
  name?: string | null;
  building_block?: string | null;
  apartment?: string | null;
  notes?: string | null;
  is_blocked?: boolean;
}

// ── Conversations & Messages ───────────────────────────────────────────

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
  created_at: string | null;
}


// ── Admin Users ────────────────────────────────────────────────────────

export type AdminRole = "superadmin" | "tenant_admin" | "tenant_viewer";

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: AdminRole;
  tenant_id: string | null;
  tenant_name: string | null;
  is_active: boolean;
  must_change_password: boolean;
  password_changed_at: string | null;
  created_at: string;
}

export interface AdminUserCreate {
  email: string;
  full_name: string;
  tenant_id: string;
}

export interface AdminUserCreateResponse {
  user: AdminUser;
  temp_password: string;
}
