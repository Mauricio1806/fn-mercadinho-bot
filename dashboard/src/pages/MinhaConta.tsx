/**
 * MinhaConta — tela do próprio usuário pra trocar senha.
 * Acessível por qualquer usuário logado (tenant_admin e platform owner).
 * O usuário troca a senha — nem o platform owner vê.
 */

import { useState, type ReactNode } from "react";
import toast from "react-hot-toast";
import { User, Mail, Lock, ShieldCheck, Save } from "lucide-react";
import { changeMyPassword } from "@/lib/api";
import { getCurrentUser, logout } from "@/lib/auth";

export function MinhaConta() {
  const user = getCurrentUser();
  const [current, setCurrent] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (!current) {
      toast.error("Informe a senha atual.");
      return;
    }
    if (newPw.length < 8) {
      toast.error("Nova senha precisa ter ao menos 8 caracteres.");
      return;
    }
    if (newPw !== confirm) {
      toast.error("As senhas não conferem.");
      return;
    }
    setSaving(true);
    try {
      await changeMyPassword(current, newPw);
      toast.success("Senha alterada! Faça login com a nova senha.");
      setTimeout(() => logout(), 1500);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Erro ao trocar senha.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Minha conta</h1>
          <p className="page-subtitle">Seus dados e senha de acesso</p>
        </div>
      </div>

      <div style={{ display: "grid", gap: 16, marginTop: 16, maxWidth: 560 }}>
        {/* Dados do usuário */}
        <div className="card" style={{ padding: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}>
            <User size={16} /> Dados pessoais
          </h2>
          <ReadOnlyField icon={<User size={14} />} label="Nome" value={user?.full_name ?? "—"} />
          <ReadOnlyField icon={<Mail size={14} />} label="Email" value={user?.email ?? "—"} />
          <p style={{ fontSize: 11.5, color: "var(--color-text-muted)", marginTop: 4 }}>
            Pra alterar nome ou email, peça ao administrador do Mercazap.
          </p>
        </div>

        {/* Trocar senha */}
        <div className="card" style={{ padding: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, margin: "0 0 6px", display: "flex", alignItems: "center", gap: 8 }}>
            <Lock size={16} /> Trocar senha
          </h2>
          <p style={{ fontSize: 12.5, color: "var(--color-text-muted)", marginBottom: 16 }}>
            Por questão de privacidade, sua senha é criptografada no banco.
          </p>

          <div style={{
            padding: 12,
            background: "rgba(34,197,94,0.10)",
            border: "1px solid rgba(34,197,94,0.30)",
            borderRadius: 8,
            marginBottom: 16,
            fontSize: 12.5,
            lineHeight: 1.6,
            display: "flex",
            gap: 10,
            alignItems: "flex-start",
          }}>
            <ShieldCheck size={16} color="rgb(34,197,94)" style={{ flexShrink: 0, marginTop: 1 }} />
            <div>
              <strong>Sua senha é só sua.</strong> O Mercazap não tem acesso à sua senha — nem o administrador da plataforma consegue ver.
              Se você esquecer, ele pode apenas gerar uma nova senha temporária pra você trocar de novo.
            </div>
          </div>

          <Field label="Senha atual">
            <input
              className="input"
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              placeholder="Digite sua senha atual"
            />
          </Field>
          <Field label="Nova senha" hint="Mínimo 8 caracteres">
            <input
              className="input"
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              placeholder="Digite uma senha forte"
            />
          </Field>
          <Field label="Confirmar nova senha">
            <input
              className="input"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Repita a nova senha"
            />
          </Field>

          <button
            className="btn btn-primary"
            onClick={submit}
            disabled={saving || !current || !newPw || !confirm}
            style={{ marginTop: 8 }}
          >
            <Save size={14} />
            {saving ? "Salvando..." : "Trocar senha"}
          </button>

          <p style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 12 }}>
            Depois de trocar a senha, você será desconectado e precisará entrar de novo com a nova senha.
          </p>
        </div>
      </div>
    </>
  );
}

function ReadOnlyField({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 11.5, color: "var(--color-text-muted)", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 }}>
        {label}
      </div>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "10px 12px",
        background: "var(--color-surface-2)",
        borderRadius: 8,
        fontSize: 13.5,
        color: "var(--color-text)",
      }}>
        <span style={{ color: "var(--color-text-muted)" }}>{icon}</span>
        {value}
      </div>
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-muted)", display: "block", marginBottom: 6 }}>
        {label}
      </label>
      {children}
      {hint && <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 4 }}>{hint}</div>}
    </div>
  );
}
