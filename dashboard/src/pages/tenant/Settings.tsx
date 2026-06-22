/**
 * Settings — configurações do tenant.
 *
 * tenant_admin: edita o próprio (PUT /api/tenants/me)
 * superadmin: vê seletor com TODOS os tenants e edita qualquer um (PATCH /api/tenants/{id})
 *
 * 6 abas: Negócio, Pix, Horário, Delivery, Persona, Branding.
 */

import {
  useState,
  useEffect,
  useRef,
  type ReactNode,
  type ChangeEvent,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  Store,
  KeyRound,
  Clock,
  Truck,
  MessageCircle,
  Palette,
  Save,
  AlertCircle,
  Upload,
} from "lucide-react";
import {
  getMyTenant,
  getTenantDetail,
  updateMyTenant,
  getTenants,
} from "@/lib/api";
import { isPlatformOwner } from "@/lib/auth";
import { Skeleton } from "@/components/ui/Skeleton";
import type {
  MyTenant,
  TenantHorario,
  TenantDelivery,
  TenantBranding,
  TenantSummary,
} from "@/lib/types";

type Tab = "negocio" | "pix" | "horario" | "delivery" | "persona" | "branding";

const TABS: { id: Tab; label: string; icon: ReactNode }[] = [
  { id: "negocio", label: "Negócio", icon: <Store size={14} /> },
  { id: "pix", label: "Pix", icon: <KeyRound size={14} /> },
  { id: "horario", label: "Horário", icon: <Clock size={14} /> },
  { id: "delivery", label: "Delivery", icon: <Truck size={14} /> },
  { id: "persona", label: "Persona", icon: <MessageCircle size={14} /> },
  { id: "branding", label: "Branding", icon: <Palette size={14} /> },
];

export function Settings() {
  const [tab, setTab] = useState<Tab>("negocio");
  const admin = isPlatformOwner();

  // Lista todos os tenants pro selector (só superadmin)
  const { data: allTenants = [] } = useQuery<TenantSummary[]>({
    queryKey: ["tenants"],
    queryFn: getTenants,
    enabled: admin,
  });

  // Qual tenant está sendo editado
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Auto-seleciona o primeiro tenant pro superadmin
  useEffect(() => {
    if (admin && allTenants.length > 0 && !selectedId) {
      setSelectedId(allTenants[0].id);
    }
  }, [admin, allTenants, selectedId]);

  // Dados do tenant em edição
  const editingId = admin ? selectedId : null;
  const queryKey = admin ? ["editing-tenant", editingId] : ["editing-tenant", "me"];
  const { data: tenant, isLoading, error } = useQuery<MyTenant>({
    queryKey,
    queryFn: () =>
      admin && editingId ? getTenantDetail(editingId) : getMyTenant(),
    enabled: admin ? !!editingId : true,
  });

  // tenantId que cada tab vai usar pro save (null = usa /me)
  const tabTenantId = admin ? selectedId : null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Configurações</h1>
          <p className="page-subtitle">
            {admin
              ? "Edite a configuração de qualquer tenant da plataforma"
              : "Como o cliente conhece, conversa e paga o seu negócio"}
          </p>
        </div>
      </div>

      {admin && (
        <TenantSelector
          tenants={allTenants}
          selectedId={selectedId}
          onChange={setSelectedId}
        />
      )}

      <TabBar active={tab} onChange={setTab} />

      <div style={{ marginTop: 20 }}>
        {isLoading ? (
          <div className="card" style={{ padding: 24, maxWidth: 720 }}>
            <Skeleton height={180} />
          </div>
        ) : error || !tenant ? (
          <ErrorBox>Falhou ao carregar a configuração do tenant.</ErrorBox>
        ) : (
          <>
            {tab === "negocio" && <NegocioTab tenant={tenant} tenantId={tabTenantId} />}
            {tab === "pix" && <PixTab tenant={tenant} tenantId={tabTenantId} />}
            {tab === "horario" && <HorarioTab tenant={tenant} tenantId={tabTenantId} />}
            {tab === "delivery" && <DeliveryTab tenant={tenant} tenantId={tabTenantId} />}
            {tab === "persona" && <PersonaTab tenant={tenant} tenantId={tabTenantId} />}
            {tab === "branding" && <BrandingTab tenant={tenant} tenantId={tabTenantId} />}
          </>
        )}
      </div>
    </>
  );
}

// ── TenantSelector ────────────────────────────────────────────────────

function TenantSelector({
  tenants,
  selectedId,
  onChange,
}: {
  tenants: TenantSummary[];
  selectedId: string | null;
  onChange: (id: string) => void;
}) {
  if (tenants.length === 0) return null;
  return (
    <div style={{
      display: "flex",
      gap: 8,
      flexWrap: "wrap",
      alignItems: "center",
      padding: "12px 16px",
      background: "var(--color-surface-2)",
      borderRadius: "var(--radius-sm)",
      marginBottom: 16,
      border: "1px solid var(--color-border)",
    }}>
      <span style={{
        fontSize: 12,
        color: "var(--color-text-muted)",
        marginRight: 4,
        fontWeight: 500,
        textTransform: "uppercase",
        letterSpacing: 0.6,
      }}>
        Tenant:
      </span>
      {tenants.map((t) => {
        const isActive = t.id === selectedId;
        return (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
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
            {t.name}
            {!t.is_active && (
              <span style={{ marginLeft: 6, opacity: 0.5 }}>· inativo</span>
            )}
          </button>
        );
      })}
    </div>
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

// ── Helper hook pra invalidar queries do tenant ──────────────────────

function useTabSave() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["editing-tenant"] });
    qc.invalidateQueries({ queryKey: ["my-tenant"] });
    qc.invalidateQueries({ queryKey: ["tenants"] });
  };
}

interface TabProps {
  tenant: MyTenant;
  tenantId: string | null;
}

// ── NegocioTab ────────────────────────────────────────────────────────

function NegocioTab({ tenant, tenantId }: TabProps) {
  const invalidate = useTabSave();
  const [name, setName] = useState(tenant.name ?? "");
  const [endereco, setEndereco] = useState((tenant.config.endereco as string) ?? "");
  const [ownersStr, setOwnersStr] = useState((tenant.config.owners ?? []).join(", "));
  const [saving, setSaving] = useState(false);

  // Reseta os campos quando muda o tenant editado
  useEffect(() => {
    setName(tenant.name ?? "");
    setEndereco((tenant.config.endereco as string) ?? "");
    setOwnersStr((tenant.config.owners ?? []).join(", "));
  }, [tenant.id]);

  async function save() {
    setSaving(true);
    try {
      const owners = ownersStr.split(",").map((s) => s.trim()).filter(Boolean);
      await updateMyTenant(
        {
          name: name.trim() || tenant.name,
          config: { endereco: endereco.trim() || undefined, owners },
        },
        tenantId,
      );
      toast.success("Negócio salvo.");
      invalidate();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard title="Negócio" subtitle="Dados que identificam seu estabelecimento">
      <Field label="Nome do negócio">
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <Field label="Endereço">
        <input
          className="input"
          placeholder="Rua, número, bairro, cidade - UF"
          value={endereco}
          onChange={(e) => setEndereco(e.target.value)}
        />
      </Field>
      <Field
        label="Telefones dos donos (separados por vírgula)"
        hint="Quem recebe notificações de pedidos. Ex: +5571999999999, +5571988888888"
      >
        <input
          className="input"
          placeholder="+5571999999999, +5571988888888"
          value={ownersStr}
          onChange={(e) => setOwnersStr(e.target.value)}
        />
      </Field>
      <SaveButton onClick={save} saving={saving} />
    </SectionCard>
  );
}

// ── PixTab ────────────────────────────────────────────────────────────

const PIX_TIPOS = [
  { v: "cnpj", l: "CNPJ" },
  { v: "cpf", l: "CPF" },
  { v: "email", l: "E-mail" },
  { v: "telefone", l: "Telefone" },
  { v: "aleatoria", l: "Chave aleatória" },
];

function PixTab({ tenant, tenantId }: TabProps) {
  const invalidate = useTabSave();
  const c = tenant.config;
  const [chave, setChave] = useState((c.pix_chave as string) ?? "");
  const [tipo, setTipo] = useState((c.pix_tipo_chave as string) ?? "cnpj");
  const [titular, setTitular] = useState((c.pix_titular as string) ?? "");
  const [banco, setBanco] = useState((c.pix_banco as string) ?? "");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setChave((c.pix_chave as string) ?? "");
    setTipo((c.pix_tipo_chave as string) ?? "cnpj");
    setTitular((c.pix_titular as string) ?? "");
    setBanco((c.pix_banco as string) ?? "");
  }, [tenant.id]);

  async function save() {
    setSaving(true);
    try {
      await updateMyTenant(
        {
          config: {
            pix_chave: chave.trim(),
            pix_tipo_chave: tipo,
            pix_titular: titular.trim(),
            pix_banco: banco.trim(),
          },
        },
        tenantId,
      );
      toast.success("Pix salvo.");
      invalidate();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard
      title="Pix"
      subtitle="Dados que o bot usa pra gerar cobrança. Sem isso, não fecha venda."
    >
      <Field label="Tipo da chave">
        <select className="input" value={tipo} onChange={(e) => setTipo(e.target.value)}>
          {PIX_TIPOS.map((t) => (<option key={t.v} value={t.v}>{t.l}</option>))}
        </select>
      </Field>
      <Field label="Chave Pix">
        <input className="input" placeholder="Ex: 60747738000149" value={chave} onChange={(e) => setChave(e.target.value)} />
      </Field>
      <Field label="Titular (nome ou razão social)">
        <input className="input" value={titular} onChange={(e) => setTitular(e.target.value)} />
      </Field>
      <Field label="Banco">
        <input className="input" placeholder="Ex: SumUp, Nubank, Inter..." value={banco} onChange={(e) => setBanco(e.target.value)} />
      </Field>
      <SaveButton onClick={save} saving={saving} />
    </SectionCard>
  );
}

// ── HorarioTab ────────────────────────────────────────────────────────

function HorarioTab({ tenant, tenantId }: TabProps) {
  const invalidate = useTabSave();
  const h: TenantHorario = (tenant.config.horario as TenantHorario) ?? {};
  const [abertura, setAbertura] = useState(h.abertura ?? "08:00");
  const [fechamento, setFechamento] = useState(h.fechamento ?? "20:00");
  const [dias, setDias] = useState(h.dias ?? "Segunda a sábado");
  const [msg, setMsg] = useState(h.msg_fora_horario ?? "Estamos fechados agora 😊");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const nh: TenantHorario = (tenant.config.horario as TenantHorario) ?? {};
    setAbertura(nh.abertura ?? "08:00");
    setFechamento(nh.fechamento ?? "20:00");
    setDias(nh.dias ?? "Segunda a sábado");
    setMsg(nh.msg_fora_horario ?? "Estamos fechados agora 😊");
  }, [tenant.id]);

  async function save() {
    setSaving(true);
    try {
      await updateMyTenant(
        { config: { horario: { abertura, fechamento, dias, msg_fora_horario: msg } } },
        tenantId,
      );
      toast.success("Horário salvo.");
      invalidate();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard title="Horário de funcionamento" subtitle="Quando o bot aceita pedidos. Fora desse horário, manda a mensagem abaixo.">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Field label="Abre às"><input type="time" className="input" value={abertura} onChange={(e) => setAbertura(e.target.value)} /></Field>
        <Field label="Fecha às"><input type="time" className="input" value={fechamento} onChange={(e) => setFechamento(e.target.value)} /></Field>
      </div>
      <Field label="Dias"><input className="input" placeholder="Ex: Segunda a sábado" value={dias} onChange={(e) => setDias(e.target.value)} /></Field>
      <Field label="Mensagem fora do horário" hint="O que o bot responde quando alguém manda mensagem fechado">
        <textarea className="input" rows={2} value={msg} onChange={(e) => setMsg(e.target.value)} />
      </Field>
      <SaveButton onClick={save} saving={saving} />
    </SectionCard>
  );
}

// ── DeliveryTab ───────────────────────────────────────────────────────

function DeliveryTab({ tenant, tenantId }: TabProps) {
  const invalidate = useTabSave();
  const d: TenantDelivery = (tenant.config.delivery as TenantDelivery) ?? {};
  const [taxaProx, setTaxaProx] = useState(String(d.taxa_proxima ?? 3));
  const [taxaDist, setTaxaDist] = useState(String(d.taxa_distante ?? 5));
  const [raio, setRaio] = useState(String(d.raio_proxima_metros ?? 500));
  const [pedidoMin, setPedidoMin] = useState(String(d.pedido_minimo ?? 15));
  const [tempo, setTempo] = useState(d.tempo_estimado ?? "15-30 min");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const nd: TenantDelivery = (tenant.config.delivery as TenantDelivery) ?? {};
    setTaxaProx(String(nd.taxa_proxima ?? 3));
    setTaxaDist(String(nd.taxa_distante ?? 5));
    setRaio(String(nd.raio_proxima_metros ?? 500));
    setPedidoMin(String(nd.pedido_minimo ?? 15));
    setTempo(nd.tempo_estimado ?? "15-30 min");
  }, [tenant.id]);

  async function save() {
    setSaving(true);
    try {
      await updateMyTenant(
        {
          config: {
            delivery: {
              taxa_proxima: parseFloat(taxaProx) || 0,
              taxa_distante: parseFloat(taxaDist) || 0,
              raio_proxima_metros: parseInt(raio, 10) || 0,
              pedido_minimo: parseFloat(pedidoMin) || 0,
              tempo_estimado: tempo.trim(),
            },
          },
        },
        tenantId,
      );
      toast.success("Delivery salvo.");
      invalidate();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard title="Delivery" subtitle="Taxas e regras que o bot aplica no cálculo do frete">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Field label="Taxa entrega próxima (R$)"><input type="number" step="0.50" className="input" value={taxaProx} onChange={(e) => setTaxaProx(e.target.value)} /></Field>
        <Field label="Taxa entrega distante (R$)"><input type="number" step="0.50" className="input" value={taxaDist} onChange={(e) => setTaxaDist(e.target.value)} /></Field>
      </div>
      <Field label="Raio considerado 'próximo' (metros)"><input type="number" className="input" value={raio} onChange={(e) => setRaio(e.target.value)} /></Field>
      <Field label="Pedido mínimo (R$)"><input type="number" step="0.50" className="input" value={pedidoMin} onChange={(e) => setPedidoMin(e.target.value)} /></Field>
      <Field label="Tempo estimado de entrega"><input className="input" placeholder="Ex: 15-30 min" value={tempo} onChange={(e) => setTempo(e.target.value)} /></Field>
      <SaveButton onClick={save} saving={saving} />
    </SectionCard>
  );
}

// ── PersonaTab ────────────────────────────────────────────────────────

function PersonaTab({ tenant, tenantId }: TabProps) {
  const invalidate = useTabSave();
  const fileRef = useRef<HTMLInputElement>(null);
  const p = (tenant.config.persona ?? {}) as Record<string, unknown>;

  const [tom, setTom] = useState<"formal" | "informal">((p.tom as "formal" | "informal") ?? "informal");
  const [emojis, setEmojis] = useState<boolean>((p.usa_emojis as boolean) ?? true);
  const [saudacao, setSaudacao] = useState((p.saudacao as string) ?? "");
  const [despedida, setDespedida] = useState((p.despedida as string) ?? "");
  const [tratamento, setTratamento] = useState((p.tratamento as string) ?? "você");
  const [markdown, setMarkdown] = useState((p.markdown_prompt as string) ?? "");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const np = (tenant.config.persona ?? {}) as Record<string, unknown>;
    setTom((np.tom as "formal" | "informal") ?? "informal");
    setEmojis((np.usa_emojis as boolean) ?? true);
    setSaudacao((np.saudacao as string) ?? "");
    setDespedida((np.despedida as string) ?? "");
    setTratamento((np.tratamento as string) ?? "você");
    setMarkdown((np.markdown_prompt as string) ?? "");
  }, [tenant.id]);

  async function handleFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const txt = await file.text();
    setMarkdown(txt);
    if (fileRef.current) fileRef.current.value = "";
    toast.success(`${file.name} carregado.`);
  }

  async function save() {
    setSaving(true);
    try {
      await updateMyTenant(
        {
          config: {
            persona: {
              ...p,
              tom,
              usa_emojis: emojis,
              saudacao: saudacao.trim(),
              despedida: despedida.trim(),
              tratamento,
              markdown_prompt: markdown,
            },
          },
        },
        tenantId,
      );
      toast.success("Persona salva.");
      invalidate();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard title="Persona do bot" subtitle="Como o bot fala com seus clientes — tom, vocabulário, abertura e fechamento">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Field label="Tom">
          <select className="input" value={tom} onChange={(e) => setTom(e.target.value as "formal" | "informal")}>
            <option value="informal">Informal (mais próximo)</option>
            <option value="formal">Formal (mais distante)</option>
          </select>
        </Field>
        <Field label="Tratamento">
          <select className="input" value={tratamento} onChange={(e) => setTratamento(e.target.value)}>
            <option value="você">você</option>
            <option value="senhor">senhor/senhora</option>
          </select>
        </Field>
      </div>
      <Field label="Usa emojis nas mensagens">
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
          <input type="checkbox" checked={emojis} onChange={(e) => setEmojis(e.target.checked)} />
          Sim, com moderação
        </label>
      </Field>
      <Field label="Saudação (primeira mensagem do bot)">
        <input className="input" placeholder="Ex: Olá! Bem-vindo ao FN Mercadinho 👋" value={saudacao} onChange={(e) => setSaudacao(e.target.value)} />
      </Field>
      <Field label="Despedida (ao fechar conversa)">
        <input className="input" placeholder="Ex: Obrigado! Volte sempre 😊" value={despedida} onChange={(e) => setDespedida(e.target.value)} />
      </Field>
      <input ref={fileRef} type="file" accept=".md,.txt" style={{ display: "none" }} onChange={handleFile} />
      <Field label="Persona estendida em Markdown (opcional)" hint="Pra prompts mais elaborados. Carregue um .md ou cole direto.">
        <div style={{ marginBottom: 8, display: "flex", gap: 12, alignItems: "center" }}>
          <button className="btn btn-ghost" onClick={() => fileRef.current?.click()} type="button" style={{ padding: "6px 12px", fontSize: 12 }}>
            <Upload size={12} />
            Carregar .md
          </button>
          <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>ou cole abaixo</span>
        </div>
        <textarea
          className="input"
          rows={10}
          style={{ fontFamily: "monospace", fontSize: 12.5, lineHeight: 1.5, resize: "vertical" }}
          placeholder="# Persona&#10;&#10;## Tom&#10;...&#10;&#10;## Regras&#10;..."
          value={markdown}
          onChange={(e) => setMarkdown(e.target.value)}
        />
      </Field>
      <SaveButton onClick={save} saving={saving} />
    </SectionCard>
  );
}

// ── BrandingTab ───────────────────────────────────────────────────────

function BrandingTab({ tenant, tenantId }: TabProps) {
  const invalidate = useTabSave();
  const b: TenantBranding = (tenant.config.branding as TenantBranding) ?? {};
  const [primaria, setPrimaria] = useState(b.cor_primaria ?? "#2E7D32");
  const [secundaria, setSecundaria] = useState(b.cor_secundaria ?? "#FFA000");
  const [logoUrl, setLogoUrl] = useState(b.logo_url ?? "");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const nb: TenantBranding = (tenant.config.branding as TenantBranding) ?? {};
    setPrimaria(nb.cor_primaria ?? "#2E7D32");
    setSecundaria(nb.cor_secundaria ?? "#FFA000");
    setLogoUrl(nb.logo_url ?? "");
  }, [tenant.id]);

  async function save() {
    setSaving(true);
    try {
      await updateMyTenant(
        {
          config: {
            branding: {
              cor_primaria: primaria,
              cor_secundaria: secundaria,
              logo_url: logoUrl.trim() || null,
            },
          },
        },
        tenantId,
      );
      toast.success("Branding salvo.");
      invalidate();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard title="Branding" subtitle="Identidade visual do painel do tenant. Aplica após o admin do tenant logar de novo.">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Field label="Cor primária">
          <div style={{ display: "flex", gap: 8 }}>
            <input type="color" value={primaria} onChange={(e) => setPrimaria(e.target.value)} style={{ width: 48, height: 38, border: "none", borderRadius: 8, cursor: "pointer" }} />
            <input className="input" value={primaria} onChange={(e) => setPrimaria(e.target.value)} style={{ fontFamily: "monospace" }} />
          </div>
        </Field>
        <Field label="Cor secundária">
          <div style={{ display: "flex", gap: 8 }}>
            <input type="color" value={secundaria} onChange={(e) => setSecundaria(e.target.value)} style={{ width: 48, height: 38, border: "none", borderRadius: 8, cursor: "pointer" }} />
            <input className="input" value={secundaria} onChange={(e) => setSecundaria(e.target.value)} style={{ fontFamily: "monospace" }} />
          </div>
        </Field>
      </div>
      <Field label="URL do logo (opcional)" hint="PNG ou JPG hospedado. Deixe em branco pra usar a inicial do nome.">
        <input className="input" placeholder="https://..." value={logoUrl} onChange={(e) => setLogoUrl(e.target.value)} />
      </Field>
      <SaveButton onClick={save} saving={saving} />
    </SectionCard>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────

function SectionCard({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="card" style={{ padding: 24, maxWidth: 720 }}>
      <h2 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 4px" }}>{title}</h2>
      <p style={{ fontSize: 13, color: "var(--color-text-muted)", margin: "0 0 20px" }}>{subtitle}</p>
      {children}
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-muted)", display: "block", marginBottom: 6 }}>{label}</label>
      {children}
      {hint && (<div style={{ fontSize: 11.5, color: "var(--color-text-muted)", marginTop: 4 }}>{hint}</div>)}
    </div>
  );
}

function SaveButton({ onClick, saving }: { onClick: () => void; saving: boolean }) {
  return (
    <button className="btn btn-primary" onClick={onClick} disabled={saving} style={{ marginTop: 8 }}>
      <Save size={14} />
      {saving ? "Salvando..." : "Salvar"}
    </button>
  );
}

function ErrorBox({ children }: { children: ReactNode }) {
  return (
    <div className="card" style={{ padding: 16, color: "var(--color-error)", background: "rgba(239,68,68,0.10)", borderColor: "rgba(239,68,68,0.30)", maxWidth: 720, display: "flex", alignItems: "center", gap: 10 }}>
      <AlertCircle size={16} />
      {children}
    </div>
  );
}
