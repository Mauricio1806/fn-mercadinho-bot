/**
 * Products — catálogo + 4 fontes de ingestão.
 *
 * Tabs: Catálogo | Importar CSV | Bling | Tiny | Webhook genérico
 * Todos os endpoints já existem no backend; este componente é wiring.
 */

import { useState, useRef, useMemo, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  Upload,
  Package,
  RefreshCw,
  Copy,
  Check,
  Search,
  Webhook,
  Boxes,
  KeyRound,
  AlertTriangle,
} from "lucide-react";
import {
  getProducts,
  importCSV,
  getIntegrationConfig,
  updateIntegrationConfig,
  triggerSync,
} from "@/lib/api";
import { getTenantId } from "@/lib/auth";
import { formatBRL } from "@/lib/format";
import { Skeleton } from "@/components/ui/Skeleton";
import type { Product } from "@/lib/types";

const PUBLIC_API_URL =
  import.meta.env.VITE_PUBLIC_API_URL ??
  "https://hospitable-flow-staging1.up.railway.app";

type Tab = "catalog" | "csv" | "bling" | "tiny" | "webhook";

const TABS: { id: Tab; label: string; icon: ReactNode }[] = [
  { id: "catalog", label: "Catálogo", icon: <Boxes size={14} /> },
  { id: "csv", label: "Importar CSV", icon: <Upload size={14} /> },
  { id: "bling", label: "Bling", icon: <KeyRound size={14} /> },
  { id: "tiny", label: "Tiny", icon: <KeyRound size={14} /> },
  { id: "webhook", label: "Webhook genérico", icon: <Webhook size={14} /> },
];

export function Products() {
  const [tab, setTab] = useState<Tab>("catalog");
  const tenantId = getTenantId();

  if (!tenantId) {
    return (
      <div style={{ padding: 24 }}>
        <ErrorBox>
          Esta página requer um tenant_admin logado. Superadmin: acesse via /admin/tenants.
        </ErrorBox>
      </div>
    );
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Produtos</h1>
          <p className="page-subtitle">
            Catálogo e fontes de ingestão (CSV, ERPs, webhooks)
          </p>
        </div>
      </div>

      <TabBar active={tab} onChange={setTab} />

      <div style={{ marginTop: 20 }}>
        {tab === "catalog" && <CatalogTab />}
        {tab === "csv" && <CSVTab tenantId={tenantId} />}
        {tab === "bling" && (
          <IntegrationTab
            tenantId={tenantId}
            system="bling"
            label="Bling"
            description="Sync via API + webhook em tempo real. Cole o access token do Bling abaixo."
            keyHint="ex: 0123456789abcdef..."
          />
        )}
        {tab === "tiny" && (
          <IntegrationTab
            tenantId={tenantId}
            system="tiny"
            label="Tiny"
            description="Sync por polling periódico. Cole a API key do Tiny abaixo."
            keyHint="ex: a1b2c3d4e5f6..."
          />
        )}
        {tab === "webhook" && <WebhookTab tenantId={tenantId} />}
      </div>
    </>
  );
}

// ── TabBar ────────────────────────────────────────────────────────────

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <div style={{
      display: "flex",
      gap: 4,
      borderBottom: "1px solid var(--color-border)",
      overflowX: "auto",
    }}>
      {TABS.map((t) => {
        const isActive = active === t.id;
        return (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "12px 16px",
              background: "none",
              border: "none",
              borderBottom: isActive
                ? "2px solid var(--color-primary)"
                : "2px solid transparent",
              color: isActive ? "var(--color-text)" : "var(--color-text-muted)",
              fontSize: 13.5,
              fontWeight: isActive ? 600 : 500,
              cursor: "pointer",
              whiteSpace: "nowrap",
              transition: "color 200ms, border-color 200ms",
            }}
          >
            {t.icon}
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

// ── CatalogTab ────────────────────────────────────────────────────────

function CatalogTab() {
  const [search, setSearch] = useState("");
  const { data: products = [], isLoading, error } = useQuery<Product[]>({
    queryKey: ["products"],
    queryFn: getProducts,
  });

  const filtered = useMemo(() => {
    if (!search.trim()) return products;
    const q = search.toLowerCase();
    return products.filter((p) => p.name.toLowerCase().includes(q));
  }, [products, search]);

  return (
    <>
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div style={{ position: "relative", flex: 1, maxWidth: 360 }}>
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
            placeholder="Buscar produtos..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: 36 }}
          />
        </div>
        <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
          {filtered.length} de {products.length}
        </span>
      </div>

      {error ? (
        <ErrorBox>Falhou ao carregar produtos.</ErrorBox>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div className="table-wrapper" style={{ border: "none", borderRadius: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Produto</th>
                  <th>Preço</th>
                  <th>Estoque</th>
                  <th>Status</th>
                  <th>Fonte</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i}><td colSpan={5}><Skeleton height={20} /></td></tr>
                  ))
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={5}>
                      <EmptyState
                        icon={<Package size={28} />}
                        title={search ? "Nada encontrado" : "Nenhum produto ainda"}
                        subtitle={
                          search
                            ? "Tenta refinar a busca."
                            : "Importe um CSV ou conecte uma fonte (Bling, Tiny, webhook)."
                        }
                      />
                    </td>
                  </tr>
                ) : (
                  filtered.map((p) => (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 500 }}>{p.name}</td>
                      <td style={{ fontWeight: 600 }}>{formatBRL(p.price)}</td>
                      <td>{p.stock_quantity != null ? p.stock_quantity : "∞"}</td>
                      <td>
                        <span className={`badge ${
                          p.is_available && p.in_stock
                            ? "badge-delivered"
                            : "badge-cancelled"
                        }`}>
                          {p.is_available && p.in_stock ? "Disponível" : "Indisponível"}
                        </span>
                      </td>
                      <td style={{
                        fontSize: 11,
                        color: "var(--color-text-muted)",
                        textTransform: "uppercase",
                        letterSpacing: 0.5,
                      }}>
                        {p.external_source ?? "manual"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}

// ── CSVTab ────────────────────────────────────────────────────────────

function CSVTab({ tenantId }: { tenantId: string }) {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const result = await importCSV(tenantId, file);
      toast.success(`✓ ${result.created} criados · ${result.updated} atualizados`);
      if (result.errors?.length) {
        toast.error(`${result.errors.length} erro(s) — confere o arquivo`);
      }
      qc.invalidateQueries({ queryKey: ["products"] });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou ao importar CSV.");
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <div className="card" style={{ padding: 24, maxWidth: 720 }}>
      <h2 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 6px" }}>
        Importar catálogo via CSV
      </h2>
      <p style={{ fontSize: 13, color: "var(--color-text-muted)", margin: "0 0 20px" }}>
        Upload manual. Use o campo <code>external_id</code> pra upsert idempotente.
      </p>

      <pre style={{
        background: "var(--color-surface-2)",
        border: "1px solid var(--color-border)",
        borderRadius: 8,
        padding: 14,
        marginBottom: 20,
        fontSize: 12,
        color: "var(--color-text)",
        fontFamily: "monospace",
        margin: "0 0 20px",
      }}>
{`nome,preco,categoria,disponivel,external_id
Coca-Cola 350ml,5.50,Bebidas,true,COCA350
Pão Francês 100g,1.20,Padaria,true,PAO100`}
      </pre>

      <input
        ref={fileRef}
        type="file"
        accept=".csv,.txt"
        style={{ display: "none" }}
        onChange={handleFile}
      />
      <button
        className="btn btn-primary"
        onClick={() => fileRef.current?.click()}
        disabled={importing}
      >
        <Upload size={14} />
        {importing ? "Importando..." : "Escolher arquivo CSV"}
      </button>
      <p style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 12 }}>
        Máximo 10 MB.
      </p>
    </div>
  );
}

// ── IntegrationTab (Bling / Tiny) ─────────────────────────────────────

interface IntegrationTabProps {
  tenantId: string;
  system: "bling" | "tiny";
  label: string;
  description: string;
  keyHint: string;
}

function IntegrationTab({
  tenantId,
  system,
  label,
  description,
  keyHint,
}: IntegrationTabProps) {
  const qc = useQueryClient();
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const { data: config, isLoading } = useQuery({
    queryKey: ["integration-config", tenantId],
    queryFn: () => getIntegrationConfig(tenantId),
  });

  const isActiveSystem = config?.sistema === system && config?.ativo === true;
  const hasKey = config?.sistema === system && config?.api_key_set === true;
  const otherActive =
    config?.sistema && config.sistema !== system && config.ativo;

  async function handleSave() {
    setSaving(true);
    try {
      const body: any = { sistema: system, ativo: true };
      if (apiKey.trim()) body.api_key = apiKey.trim();
      await updateIntegrationConfig(tenantId, body);
      toast.success(`${label} configurado.`);
      setApiKey("");
      qc.invalidateQueries({ queryKey: ["integration-config", tenantId] });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate() {
    setSaving(true);
    try {
      await updateIntegrationConfig(tenantId, { ativo: false });
      toast.success(`${label} desativado.`);
      qc.invalidateQueries({ queryKey: ["integration-config", tenantId] });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    try {
      const r = await triggerSync(tenantId);
      toast.success(`Sync ok — ${r.created} criados · ${r.updated} atualizados`);
      qc.invalidateQueries({ queryKey: ["products"] });
      if (r.errors?.length) toast.error(`${r.errors.length} erro(s) no sync`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Sync falhou.");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="card" style={{ padding: 24, maxWidth: 720 }}>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        marginBottom: 6,
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
          Integração {label}
        </h2>
        <StatusBadge
          state={isActiveSystem ? "active" : hasKey ? "configured" : "inactive"}
        />
      </div>
      <p style={{ fontSize: 13, color: "var(--color-text-muted)", margin: "0 0 20px" }}>
        {description}
      </p>

      {isLoading ? (
        <Skeleton height={120} />
      ) : (
        <>
          <div style={{ marginBottom: 16 }}>
            <label style={{
              fontSize: 12,
              fontWeight: 500,
              color: "var(--color-text-muted)",
              display: "block",
              marginBottom: 6,
            }}>
              API Key
              {hasKey && (
                <span style={{ marginLeft: 8, color: "var(--color-success)" }}>
                  · configurada ({config?.api_key_preview})
                </span>
              )}
            </label>
            <input
              type="password"
              className="input"
              placeholder={hasKey ? "Em branco mantém a atual" : keyHint}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              autoComplete="off"
            />
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <button
              className="btn btn-primary"
              onClick={handleSave}
              disabled={saving || (!apiKey.trim() && !hasKey)}
            >
              {saving ? "Salvando..." : hasKey && isActiveSystem ? "Atualizar" : "Conectar"}
            </button>
            {hasKey && isActiveSystem && (
              <button
                className="btn btn-ghost"
                onClick={handleSync}
                disabled={syncing}
              >
                <RefreshCw
                  size={13}
                  style={syncing ? { animation: "spin 1s linear infinite" } : undefined}
                />
                {syncing ? "Sincronizando..." : "Sincronizar tudo"}
              </button>
            )}
            {isActiveSystem && (
              <button
                className="btn btn-ghost"
                onClick={handleDeactivate}
                disabled={saving}
                style={{ marginLeft: "auto", color: "var(--color-error)" }}
              >
                Desativar
              </button>
            )}
          </div>

          {otherActive && !isActiveSystem && (
            <div style={{
              marginTop: 16,
              padding: 12,
              borderRadius: 8,
              background: "rgba(245,158,11,0.10)",
              border: "1px solid rgba(245,158,11,0.30)",
              fontSize: 12.5,
              color: "var(--color-warning)",
              display: "flex",
              gap: 10,
              alignItems: "flex-start",
            }}>
              <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
              <span>
                Outra fonte está ativa: <strong>{config?.sistema}</strong>.
                Salvar aqui vai trocar a integração ativa pra {label}.
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── WebhookTab ────────────────────────────────────────────────────────

function WebhookTab({ tenantId }: { tenantId: string }) {
  const qc = useQueryClient();
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);

  const { data: config, isLoading } = useQuery({
    queryKey: ["integration-config", tenantId],
    queryFn: () => getIntegrationConfig(tenantId),
  });

  const webhookUrl = `${PUBLIC_API_URL}/api/integrations/${tenantId}/webhook`;
  const isActive = config?.sistema === "webhook" && config?.ativo === true;

  function copy() {
    navigator.clipboard.writeText(webhookUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function toggle() {
    setSaving(true);
    try {
      await updateIntegrationConfig(tenantId, {
        sistema: isActive ? null : "webhook",
        ativo: !isActive,
      });
      toast.success(isActive ? "Webhook desativado." : "Webhook ativado.");
      qc.invalidateQueries({ queryKey: ["integration-config", tenantId] });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card" style={{ padding: 24, maxWidth: 720 }}>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        marginBottom: 6,
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
          Webhook genérico
        </h2>
        <StatusBadge state={isActive ? "active" : "inactive"} />
      </div>
      <p style={{ fontSize: 13, color: "var(--color-text-muted)", margin: "0 0 20px" }}>
        Aceita POST de qualquer sistema. Payload flexível em PT ou EN.
        Sem credenciais — o tenant_id na URL é o controle.
      </p>

      {isLoading ? (
        <Skeleton height={180} />
      ) : (
        <>
          <label style={{
            fontSize: 12,
            fontWeight: 500,
            color: "var(--color-text-muted)",
            display: "block",
            marginBottom: 6,
          }}>
            URL pra apontar o ERP do cliente
          </label>
          <div style={{ display: "flex", gap: 6, marginBottom: 20 }}>
            <input
              className="input"
              value={webhookUrl}
              readOnly
              style={{ fontFamily: "monospace", fontSize: 12 }}
            />
            <button className="btn btn-ghost" onClick={copy} style={{ flexShrink: 0 }}>
              {copied ? <Check size={13} /> : <Copy size={13} />}
              {copied ? "Copiado" : "Copiar"}
            </button>
          </div>

          <label style={{
            fontSize: 12,
            fontWeight: 500,
            color: "var(--color-text-muted)",
            display: "block",
            marginBottom: 6,
          }}>
            Exemplo de payload (aceita PT e EN)
          </label>
          <pre style={{
            background: "var(--color-surface-2)",
            border: "1px solid var(--color-border)",
            borderRadius: 8,
            padding: 14,
            fontSize: 12,
            color: "var(--color-text)",
            margin: "0 0 20px",
            overflowX: "auto",
            fontFamily: "monospace",
          }}>
{`{
  "external_id": "SKU001",
  "name": "Coca-Cola 350ml",
  "price": 5.50,
  "category": "Bebidas",
  "available": true,
  "stock_quantity": 24
}`}
          </pre>

          <button
            className={isActive ? "btn btn-ghost" : "btn btn-primary"}
            onClick={toggle}
            disabled={saving}
            style={isActive ? { color: "var(--color-error)" } : undefined}
          >
            {saving
              ? "Aguarde..."
              : isActive
                ? "Desativar como fonte oficial"
                : "Ativar como fonte do catálogo"}
          </button>
          <p style={{ fontSize: 11.5, color: "var(--color-text-muted)", marginTop: 10 }}>
            O endpoint recebe POSTs sempre. Ativar marca o webhook como handler
            oficial do tenant (impacta o roteador interno).
          </p>
        </>
      )}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────

function StatusBadge({ state }: { state: "active" | "configured" | "inactive" }) {
  const map = {
    active: { label: "Ativo", cls: "badge-delivered" },
    configured: { label: "Configurado", cls: "badge-payment_confirmed" },
    inactive: { label: "Inativo", cls: "badge-cancelled" },
  };
  const { label, cls } = map[state];
  return <span className={`badge ${cls}`}>{label}</span>;
}

function EmptyState({
  icon, title, subtitle,
}: { icon: ReactNode; title: string; subtitle: string }) {
  return (
    <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--color-text-muted)" }}>
      <div style={{
        display: "inline-flex",
        width: 56, height: 56, borderRadius: 16,
        background: "var(--color-surface-2)",
        alignItems: "center", justifyContent: "center",
        marginBottom: 12,
      }}>
        {icon}
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)" }}>{title}</div>
      <div style={{ fontSize: 12, marginTop: 4 }}>{subtitle}</div>
    </div>
  );
}

function ErrorBox({ children }: { children: ReactNode }) {
  return (
    <div style={{
      background: "rgba(239,68,68,0.10)",
      border: "1px solid rgba(239,68,68,0.30)",
      borderRadius: "var(--radius-sm)",
      padding: "12px 16px",
      color: "var(--color-error)",
      fontSize: 13,
      display: "flex",
      alignItems: "center",
      gap: 10,
    }}>
      <AlertTriangle size={14} />
      {children}
    </div>
  );
}
