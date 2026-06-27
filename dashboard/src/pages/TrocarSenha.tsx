/**
 * Tela forçada quando must_change_password=true no JWT.
 * Usuário não consegue navegar pra outra rota até trocar.
 */

import { useState } from "react";
import toast from "react-hot-toast";
import { Lock } from "lucide-react";
import { changeMyPassword, login as apiLogin } from "@/lib/api";
import { saveTokens, getCurrentUser } from "@/lib/auth";

export function TrocarSenha() {
  const user = getCurrentUser();
  const [current, setCurrent] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (newPw.length < 8) {
      toast.error("Nova senha precisa de ao menos 8 caracteres.");
      return;
    }
    if (newPw !== confirm) {
      toast.error("As senhas não conferem.");
      return;
    }
    setSaving(true);
    try {
      await changeMyPassword(current, newPw);
      // Re-login com a senha nova pra atualizar o JWT (sem o flag must_change_password)
      const tokens = await apiLogin(user!.email, newPw);
      saveTokens(tokens.access_token, tokens.refresh_token);
      toast.success("Senha atualizada.");
      window.location.href = "/dashboard";
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Erro ao trocar senha.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--color-bg)",
        padding: 20,
      }}
    >
      <div className="card" style={{ padding: 32, maxWidth: 420, width: "100%" }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div
            style={{
              display: "inline-flex",
              width: 56,
              height: 56,
              borderRadius: 16,
              background: "var(--color-primary-light)",
              color: "var(--color-primary)",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 12,
            }}
          >
            <Lock size={24} />
          </div>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Troca de senha obrigatória</h1>
          <p style={{ fontSize: 13, color: "var(--color-text-muted)", marginTop: 6 }}>
            Você está usando a senha temporária. Defina uma nova senha pra continuar.
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Field label="Senha atual (temporária)">
            <input
              className="input"
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              autoFocus
            />
          </Field>
          <Field label="Nova senha" hint="Mínimo 8 caracteres">
            <input
              className="input"
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
            />
          </Field>
          <Field label="Confirmar nova senha">
            <input
              className="input"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </Field>
          <button
            className="btn btn-primary"
            onClick={submit}
            disabled={saving || !current || !newPw || !confirm}
            style={{ marginTop: 8 }}
          >
            {saving ? "Salvando..." : "Trocar senha"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ fontSize: 12, color: "var(--color-text-muted)", display: "block", marginBottom: 6 }}>
        {label}
      </label>
      {children}
      {hint && <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 4 }}>{hint}</div>}
    </div>
  );
}
