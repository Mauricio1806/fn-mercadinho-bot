/**
 * Settings — configurações do tenant (visíveis e editáveis pelo próprio tenant_admin).
 *
 * 6 abas: Negócio, Pix, Horário, Delivery, Persona, Branding.
 * Cada aba carrega do mesmo query (/api/tenants/me), edita sua seção e salva via PUT /me.
 */

import { useState, useEffect, type ReactNode } from "react";
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
} from "lucide-react";
import { getMyTenant, updateMyTenant } from "@/lib/api";
import { Skeleton } from "@/components/ui/Skeleton";
import type {
  MyTenant,
  TenantHorario,
  TenantDelivery,
  TenantPersona,
  TenantBranding,
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
  const { data: tenant, isLoading, error } = useQuery<MyTenant>({
    queryKey: ["my-tenant"],
    queryFn: getMyTenant,
  });

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Configurações</h1>
          <p className="page-subtitle">
            Como o cliente conhece, conversa e paga o seu negócio
          </p>
        </div>
      </div>

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
            {tab === "negocio" && <NegocioTab tenant={tenant} />}
            {tab === "pix" && <PixTab tenant={tenant} />}
            {tab === "horario" && <HorarioTab tenant={tenant} />}
            {tab === "delivery" && <DeliveryTab tenant={tenant} />}
            {tab === "persona" && <PersonaTab tenant={tenant} />}
            {tab === "branding" && <BrandingTab tenant={tenant} />}
          </>
        )}
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

// ── NegocioTab ────────────────────────────────────────────────────────

function NegocioTab({ tenant }: { tenant: MyTenant }) {
  const qc = useQueryClient();
  const [name, setName] = useState(tenant.name);
  const [endereco, setEndereco] = useState(tenant.config.endereco ?? "");
  const [ownersStr, setOwnersStr] = useState(
    (tenant.config.owners ?? []).join(", ")
  );
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      const owners = ownersStr
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      await updateMyTenant({
        name: name.trim() || tenant.name,
        config: { endereco: endereco.trim() || undefined, owners },
      });
      toast.success("Negócio salvo.");
      qc.invalidateQueries({ queryKey: ["my-tenant"] });
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

function PixTab({ tenant }: { tenant: MyTenant }) {
  const qc = useQueryClient();
  const c = tenant.config;
  const [chave, setChave] = useState(c.pix_chave ?? "");
  const [tipo, setTipo] = useState(c.pix_tipo_chave ?? "cnpj");
  const [titular, setTitular] = useState(c.pix_titular ?? "");
  const [banco, setBanco] = useState(c.pix_banco ?? "");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await updateMyTenant({
        config: {
          pix_chave: chave.trim(),
          pix_tipo_chave: tipo,
          pix_titular: titular.trim(),
          pix_banco: banco.trim(),
        },
      });
      toast.success("Pix salvo.");
      qc.invalidateQueries({ queryKey: ["my-tenant"] });
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
          {PIX_TIPOS.map((t) => (
            <option key={t.v} value={t.v}>{t.l}</option>
          ))}
        </select>
      </Field>
      <Field label="Chave Pix">
        <input
          className="input"
          placeholder="Ex: 60747738000149"
          value={chave}
          onChange={(e) => setChave(e.target.value)}
        />
      </Field>
      <Field label="Titular (nome ou razão social)">
        <input
          className="input"
          value={titular}
          onChange={(e) => setTitular(e.target.value)}
        />
      </Field>
      <Field label="Banco">
        <input
          className="input"
          placeholder="Ex: SumUp, Nubank, Inter..."
          value={banco}
          onChange={(e) => setBanco(e.target.value)}
        />
      </Field>
      <SaveButton onClick={save} saving={saving} />
    </SectionCard>
  );
}

// ── HorarioTab ────────────────────────────────────────────────────────

function HorarioTab({ tenant }: { tenant: MyTenant }) {
  const qc = useQueryClient();
  const h: TenantHorario = tenant.config.horario ?? {};
  const [abertura, setAbertura] = useState(h.abertura ?? "08:00");
  const [fechamento, setFechamento] = useState(h.fechamento ?? "20:00");
  const [dias, setDias] = useState(h.dias ?? "Segunda a sábado");
  const [msg, setMsg] = useState(h.msg_fora_horario ?? "Estamos fechados agora 😊");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await updateMyTenant({
        config: {
          horario: { abertura, fechamento, dias, msg_fora_horario: msg },
        },
      });
      toast.success("Horário salvo.");
      qc.invalidateQueries({ queryKey: ["my-tenant"] });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard
      title="Horário de funcionamento"
      subtitle="Quando o bot aceita pedidos. Fora desse horário, manda a mensagem abaixo."
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Field label="Abre às">
          <input
            type="time"
            className="input"
            value={abertura}
            onChange={(e) => setAbertura(e.target.value)}
          />
        </Field>
        <Field label="Fecha às">
          <input
            type="time"
            className="input"
            value={fechamento}
            onChange={(e) => setFechamento(e.target.value)}
          />
        </Field>
      </div>
      <Field label="Dias">
        <input
          className="input"
          placeholder="Ex: Segunda a sábado"
          value={dias}
          onChange={(e) => setDias(e.target.value)}
        />
      </Field>
      <Field
        label="Mensagem fora do horário"
        hint="O que o bot responde quando alguém manda mensagem fechado"
      >
        <textarea
          className="input"
          rows={2}
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
        />
      </Field>
      <SaveButton onClick={save} saving={saving} />
    </SectionCard>
  );
}

// ── DeliveryTab ───────────────────────────────────────────────────────

function DeliveryTab({ tenant }: { tenant: MyTenant }) {
  const qc = useQueryClient();
  const d: TenantDelivery = tenant.config.delivery ?? {};
  const [taxaProx, setTaxaProx] = useState(String(d.taxa_proxima ?? 3));
  const [taxaDist, setTaxaDist] = useState(String(d.taxa_distante ?? 5));
  const [raio, setRaio] = useState(String(d.raio_proxima_metros ?? 500));
  const [pedidoMin, setPedidoMin] = useState(String(d.pedido_minimo ?? 15));
  const [tempo, setTempo] = useState(d.tempo_estimado ?? "15-30 min");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await updateMyTenant({
        config: {
          delivery: {
            taxa_proxima: parseFloat(taxaProx) || 0,
            taxa_distante: parseFloat(taxaDist) || 0,
            raio_proxima_metros: parseInt(raio, 10) || 0,
            pedido_minimo: parseFloat(pedidoMin) || 0,
            tempo_estimado: tempo.trim(),
          },
        },
      });
      toast.success("Delivery salvo.");
      qc.invalidateQueries({ queryKey: ["my-tenant"] });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard
      title="Delivery"
      subtitle="Taxas e regras que o bot aplica no cálculo do frete"
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Field label="Taxa entrega próxima (R$)">
          <input
            type="number"
            step="0.50"
            className="input"
            value={taxaProx}
            onChange={(e) => setTaxaProx(e.target.value)}
          />
        </Field>
        <Field label="Taxa entrega distante (R$)">
          <input
            type="number"
            step="0.50"
            className="input"
            value={taxaDist}
            onChange={(e) => setTaxaDist(e.target.value)}
          />
        </Field>
      </div>
      <Field label="Raio considerado 'próximo' (metros)">
        <input
          type="number"
          className="input"
          value={raio}
          onChange={(e) => setRaio(e.target.value)}
        />
      </Field>
      <Field label="Pedido mínimo (R$)">
        <input
          type="number"
          step="0.50"
          className="input"
          value={pedidoMin}
          onChange={(e) => setPedidoMin(e.target.value)}
        />
      </Field>
      <Field label="Tempo estimado de entrega">
        <input
          className="input"
          placeholder="Ex: 15-30 min"
          value={tempo}
          onChange={(e) => setTempo(e.target.value)}
        />
      </Field>
      <SaveButton onClick={save} saving={saving} />
    </SectionCard>
  );
}

// ── PersonaTab ────────────────────────────────────────────────────────

function PersonaTab({ tenant }: { tenant: MyTenant }) {
  const qc = useQueryClient();
  const p: TenantPersona = tenant.config.persona ?? {};
  const [tom, setTom] = useState<"formal" | "informal">(
    (p.tom as any) ?? "informal"
  );
  const [emojis, setEmojis] = useState<boolean>(p.usa_emojis ?? true);
  const [saudacao, setSaudacao] = useState(p.saudacao ?? "");
  const [despedida, setDespedida] = useState(p.despedida ?? "");
  const [tratamento, setTratamento] = useState(p.tratamento ?? "você");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await updateMyTenant({
        config: {
          persona: {
            tom,
            usa_emojis: emojis,
            saudacao: saudacao.trim(),
            despedida: despedida.trim(),
            tratamento,
          },
        },
      });
      toast.success("Persona salva.");
      qc.invalidateQueries({ queryKey: ["my-tenant"] });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard
      title="Persona do bot"
      subtitle="Como o bot fala com seus clientes — tom, vocabulário, abertura e fechamento"
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Field label="Tom">
          <select
            className="input"
            value={tom}
            onChange={(e) => setTom(e.target.value as any)}
          >
            <option value="informal">Informal (mais próximo)</option>
            <option value="formal">Formal (mais distante)</option>
          </select>
        </Field>
        <Field label="Tratamento">
          <select
            className="input"
            value={tratamento}
            onChange={(e) => setTratamento(e.target.value)}
          >
            <option value="você">você</option>
            <option value="senhor">senhor/senhora</option>
          </select>
        </Field>
      </div>
      <Field label="Usa emojis nas mensagens">
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
          <input
            type="checkbox"
            checked={emojis}
            onChange={(e) => setEmojis(e.target.checked)}
          />
          Sim, com moderação
        </label>
      </Field>
      <Field label="Saudação (primeira mensagem do bot)">
        <input
          className="input"
          placeholder="Ex: Olá! Bem-vindo ao FN Mercadinho 👋"
          value={saudacao}
          onChange={(e) => setSaudacao(e.target.value)}
        />
      </Field>
      <Field label="Despedida (ao fechar conversa)">
        <input
          className="input"
          placeholder="Ex: Obrigado! Volte sempre 😊"
          value={despedida}
          onChange={(e) => setDespedida(e.target.value)}
        />
      </Field>
      <SaveButton onClick={save} saving={saving} />
    </SectionCard>
  );
}

// ── BrandingTab ───────────────────────────────────────────────────────

function BrandingTab({ tenant }: { tenant: MyTenant }) {
  const qc = useQueryClient();
  const b: TenantBranding = tenant.config.branding ?? {};
  const [primaria, setPrimaria] = useState(b.cor_primaria ?? "#2E7D32");
  const [secundaria, setSecundaria] = useState(b.cor_secundaria ?? "#FFA000");
  const [logoUrl, setLogoUrl] = useState(b.logo_url ?? "");
  const [saving, setSaving] = useState(false);

  // Preview ao vivo
  useEffect(() => {
    document.documentElement.style.setProperty("--color-primary", primaria);
  }, [primaria]);

  async function save() {
    setSaving(true);
    try {
      await updateMyTenant({
        config: {
          branding: {
            cor_primaria: primaria,
            cor_secundaria: secundaria,
            logo_url: logoUrl.trim() || null,
          },
        },
      });
      toast.success("Branding salvo.");
      qc.invalidateQueries({ queryKey: ["my-tenant"] });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Falhou ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard
      title="Branding"
      subtitle="Identidade visual do seu painel. O cliente final não vê isso — é só pra você."
    >
      <div style={{
        background: "rgba(245,158,11,0.10)",
        border: "1px solid rgba(245,158,11,0.30)",
        borderRadius: 8,
        padding: 12,
        fontSize: 12.5,
        color: "var(--color-warning)",
        marginBottom: 16,
        display: "flex",
        gap: 10,
      }}>
        <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
        <span>
          A cor primária é aplicada na hora pra preview, mas pra aplicar de
          forma permanente em todo o painel você precisa sair e entrar de novo
          (a cor vive no JWT).
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Field label="Cor primária">
          <div style={{ display: "flex", gap: 8 }}>
            <input
              type="color"
              value={primaria}
              onChange={(e) => setPrimaria(e.target.value)}
              style={{ width: 48, height: 38, border: "none", borderRadius: 8, cursor: "pointer" }}
            />
            <input
              className="input"
              value={primaria}
              onChange={(e) => setPrimaria(e.target.value)}
              style={{ fontFamily: "monospace" }}
            />
          </div>
        </Field>
        <Field label="Cor secundária">
          <div style={{ display: "flex", gap: 8 }}>
            <input
              type="color"
              value={secundaria}
              onChange={(e) => setSecundaria(e.target.value)}
              style={{ width: 48, height: 38, border: "none", borderRadius: 8, cursor: "pointer" }}
            />
            <input
              className="input"
              value={secundaria}
              onChange={(e) => setSecundaria(e.target.value)}
              style={{ fontFamily: "monospace" }}
            />
          </div>
        </Field>
      </div>
      <Field label="URL do logo (opcional)" hint="PNG ou JPG hospedado. Deixe em branco pra usar a inicial do nome.">
        <input
          className="input"
          placeholder="https://..."
          value={logoUrl}
          onChange={(e) => setLogoUrl(e.target.value)}
        />
      </Field>
      <SaveButton onClick={save} saving={saving} />
    </SectionCard>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────

function SectionCard({
  title, subtitle, children,
}: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="card" style={{ padding: 24, maxWidth: 720 }}>
      <h2 style={{ fontSize: 16, fontWeight: 600, margin: "0 0 4px" }}>{title}</h2>
      <p style={{ fontSize: 13, color: "var(--color-text-muted)", margin: "0 0 20px" }}>
        {subtitle}
      </p>
      {children}
    </div>
  );
}

function Field({
  label, hint, children,
}: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{
        fontSize: 12,
        fontWeight: 500,
        color: "var(--color-text-muted)",
        display: "block",
        marginBottom: 6,
      }}>
        {label}
      </label>
      {children}
      {hint && (
        <div style={{
          fontSize: 11.5,
          color: "var(--color-text-muted)",
          marginTop: 4,
        }}>
          {hint}
        </div>
      )}
    </div>
  );
}

function SaveButton({ onClick, saving }: { onClick: () => void; saving: boolean }) {
  return (
    <button
      className="btn btn-primary"
      onClick={onClick}
      disabled={saving}
      style={{ marginTop: 8 }}
    >
      <Save size={14} />
      {saving ? "Salvando..." : "Salvar"}
    </button>
  );
}

function ErrorBox({ children }: { children: ReactNode }) {
  return (
    <div className="card" style={{
      padding: 16,
      color: "var(--color-error)",
      background: "rgba(239,68,68,0.10)",
      borderColor: "rgba(239,68,68,0.30)",
      maxWidth: 720,
      display: "flex",
      alignItems: "center",
      gap: 10,
    }}>
      <AlertCircle size={16} />
      {children}
    </div>
  );
}
