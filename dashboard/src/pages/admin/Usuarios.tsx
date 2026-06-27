/**
 * Usuarios — gestão de admins (platform owner only).
 */

import { useState, type ReactNode } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { UserPlus, Copy, Power, KeyRound, X } from "lucide-react";
import {
  listAdminUsers,
  createAdminUser,
  updateAdminUser,
  getTenants,
} from "@/lib/api";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDateTime } from "@/lib/format";
import type { AdminUser, TenantSummary } from "@/lib/types";

export function Usuarios() {
  const [showCreate, setShowCreate] = useState(false);
  const [tempPwModal, setTempPwModal] = useState<{ email: string; pw: string } | null>(null);

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: listAdminUsers,
  });

  const { data: tenants = [] } = useQuery({
    queryKey: ["tenants"],
    queryFn: getTenants,
  });

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Usuários</h1>
          <p className="page-subtitle">Admins de cada tenant</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <UserPlus size={14} /> Novo usuário
        </button>
      </div>

      <div style={{ marginTop: 16 }}>
        {isLoading ? (
          <div className="card" style={{ padding: 24 }}><Skeleton height={200} /></div>
        ) : (
          <UserTable users={users} onTempPw={setTempPwModal} />
        )}
      </div>

      {showCreate && (
        <CreateModal
          tenants={tenants}
          onClose={() => setShowCreate(false)}
          onCreated={(email, pw) => { setShowCreate(false); setTempPwModal({ email, pw }); }}
        />
      )}

      {tempPwModal && (
        <TempPwModal email={tempPwModal.email} pw={tempPwModal.pw} onClose={() => setTempPwModal(null)} />
      )}
    </>
  );
}

function UserTable({ users, onTempPw }: { users: AdminUser[]; onTempPw: (m: { email: string; pw: string }) => void }) {
  const qc = useQueryClient();

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => updateAdminUser(id, { is_active }),
    onSuccess: () => { toast.success("Atualizado."); qc.invalidateQueries({ queryKey: ["admin-users"] }); },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? "Erro."),
  });

  const resetPw = useMutation({
    mutationFn: (id: string) => updateAdminUser(id, { reset_password: true }),
    onSuccess: (data, id) => {
      const user = users.find((u) => u.id === id);
      if (data.temp_password && user) onTempPw({ email: user.email, pw: data.temp_password });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? "Erro."),
  });

  if (users.length === 0) {
    return <div className="card" style={{ padding: 40, textAlign: "center", color: "var(--color-text-muted)" }}>Nenhum usuário cadastrado.</div>;
  }

  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "var(--color-surface-2)", borderBottom: "1px solid var(--color-border)" }}>
            <Th>Usuário</Th><Th>Tenant</Th><Th>Role</Th><Th>Status</Th><Th>Senha</Th><Th align="right">Ações</Th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
              <Td>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{u.full_name}</div>
                <div style={{ fontSize: 11.5, color: "var(--color-text-muted)", marginTop: 2 }}>{u.email}</div>
              </Td>
              <Td><div style={{ fontSize: 12.5 }}>{u.tenant_name ?? "—"}</div></Td>
              <Td><Chip>{u.role}</Chip></Td>
              <Td>
                {u.is_active ? <Chip color="rgb(34,197,94)">Ativo</Chip> : <Chip color="rgb(239,68,68)">Inativo</Chip>}
              </Td>
              <Td>
                {u.must_change_password ? <Chip color="rgb(245,158,11)">Pendente troca</Chip> : (
                  <div style={{ fontSize: 11.5, color: "var(--color-text-muted)" }}>
                    {u.password_changed_at ? formatDateTime(u.password_changed_at) : "—"}
                  </div>
                )}
              </Td>
              <Td align="right">
                <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                  <button className="btn btn-ghost" onClick={() => resetPw.mutate(u.id)} disabled={resetPw.isPending}
                    style={{ padding: "4px 10px", fontSize: 11.5 }} title="Resetar senha">
                    <KeyRound size={12} /> Reset
                  </button>
                  <button className="btn btn-ghost" onClick={() => toggleActive.mutate({ id: u.id, is_active: !u.is_active })}
                    disabled={toggleActive.isPending}
                    style={{ padding: "4px 10px", fontSize: 11.5, color: u.is_active ? "rgb(239,68,68)" : "rgb(34,197,94)" }}
                    title={u.is_active ? "Desligar" : "Reativar"}>
                    <Power size={12} /> {u.is_active ? "Desligar" : "Ativar"}
                  </button>
                </div>
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CreateModal({ tenants, onClose, onCreated }: { tenants: TenantSummary[]; onClose: () => void; onCreated: (email: string, pw: string) => void }) {
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [tenantId, setTenantId] = useState(tenants[0]?.id ?? "");

  const create = useMutation({
    mutationFn: () => createAdminUser({ email, full_name: fullName, tenant_id: tenantId }),
    onSuccess: (data) => { qc.invalidateQueries({ queryKey: ["admin-users"] }); onCreated(data.user.email, data.temp_password); },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? "Erro."),
  });

  return (
    <ModalShell title="Novo usuário" onClose={onClose}>
      <Field label="Tenant">
        <select className="input" value={tenantId} onChange={(e) => setTenantId(e.target.value)}>
          {tenants.map((t) => (<option key={t.id} value={t.id}>{t.name}</option>))}
        </select>
      </Field>
      <Field label="Nome completo">
        <input className="input" value={fullName} onChange={(e) => setFullName(e.target.value)} />
      </Field>
      <Field label="Email">
        <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="cliente@empresa.com" />
      </Field>
      <div style={{
        marginTop: 4,
        padding: 10,
        background: "var(--color-surface-2)",
        borderRadius: 8,
        fontSize: 11.5,
        lineHeight: 1.6,
        color: "var(--color-text-muted)",
      }}>
        📋 Ao clicar em "Criar usuário", uma <strong>senha temporária</strong> é gerada
        automaticamente e aparece UMA vez na próxima tela.
        <br /><br />
        🔒 Copie e envie pro cliente — depois disso, ninguém (nem você) vê a senha de novo.
        O cliente troca a senha no primeiro login e ela passa a ser só dele.
      </div>
      <button className="btn btn-primary" onClick={() => create.mutate()}
        disabled={create.isPending || !email || !fullName || !tenantId}
        style={{ marginTop: 12, width: "100%" }}>
        <UserPlus size={14} /> {create.isPending ? "Criando..." : "Criar usuário"}
      </button>
    </ModalShell>
  );
}

function TempPwModal({ email, pw, onClose }: { email: string; pw: string; onClose: () => void }) {
  const copy = () => { navigator.clipboard.writeText(pw); toast.success("Senha copiada."); };
  return (
    <ModalShell title="Senha temporária gerada" onClose={onClose}>
      <div style={{
        padding: 12,
        background: "rgba(245,158,11,0.10)",
        border: "1px solid rgba(245,158,11,0.30)",
        borderRadius: 8,
        marginBottom: 12,
        fontSize: 12.5,
        lineHeight: 1.6,
      }}>
        ⚠️ <strong>Anota ou copia AGORA.</strong> Esta senha não aparece de novo.
        Depois que o cliente trocar no primeiro login, fica privada — você não vê mais.
      </div>
      <div style={{ background: "var(--color-surface-2)", padding: 16, borderRadius: 8, marginBottom: 12 }}>
        <div style={{ fontSize: 11.5, color: "var(--color-text-muted)", marginBottom: 4 }}>EMAIL</div>
        <div style={{ fontSize: 13, fontFamily: "monospace", marginBottom: 12 }}>{email}</div>
        <div style={{ fontSize: 11.5, color: "var(--color-text-muted)", marginBottom: 4 }}>SENHA</div>
        <div style={{ fontSize: 18, fontFamily: "monospace", fontWeight: 600, letterSpacing: 1 }}>{pw}</div>
      </div>
      <button className="btn btn-primary" onClick={copy} style={{ width: "100%" }}>
        <Copy size={14} /> Copiar senha
      </button>
    </ModalShell>
  );
}

function ModalShell({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 100 }} />
      <div style={{
        position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
        background: "var(--color-surface)", border: "1px solid var(--color-border)",
        borderRadius: 12, padding: 24, width: "90%", maxWidth: 420, zIndex: 101,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>{title}</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--color-text-muted)" }}>
            <X size={18} />
          </button>
        </div>
        {children}
      </div>
    </>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-muted)", marginBottom: 6 }}>{label}</div>
      {children}
    </div>
  );
}

function Th({ children, align = "left" }: { children?: ReactNode; align?: "left" | "right" }) {
  return <th style={{ textAlign: align, padding: "12px 16px", fontSize: 11, fontWeight: 500, color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: 0.5 }}>{children}</th>;
}

function Td({ children, align = "left" }: { children?: ReactNode; align?: "left" | "right" }) {
  return <td style={{ padding: "12px 16px", fontSize: 13, textAlign: align, verticalAlign: "top" }}>{children}</td>;
}

function Chip({ children, color }: { children: ReactNode; color?: string }) {
  return (
    <span style={{
      fontSize: 10.5, padding: "2px 8px", borderRadius: 99,
      background: color ? color + "1A" : "var(--color-surface-2)",
      color: color ?? "var(--color-text-muted)",
      fontWeight: 500, border: "1px solid var(--color-border)",
    }}>
      {children}
    </span>
  );
}
