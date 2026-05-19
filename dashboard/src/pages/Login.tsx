/**
 * Login page — autenticação multi-tenant.
 * Detecta role do JWT e redireciona para a área correta.
 */

import { useState, type FormEvent } from "react";
import { login, saveTokens } from "@/lib/auth";
import { login as apiLogin } from "@/lib/api";
import { getBranding } from "@/lib/auth";
import toast from "react-hot-toast";

interface LoginProps {
  onSuccess: () => void;
}

export function Login({ onSuccess }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const branding = getBranding();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email || !password) return;

    setLoading(true);
    try {
      const { access_token, refresh_token } = await apiLogin(email, password);
      saveTokens(access_token, refresh_token);
      toast.success("Login realizado!");
      onSuccess();
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? "Email ou senha incorretos.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  const firstLetter = branding.tenant_name.charAt(0).toUpperCase();

  return (
    <div className="login-page">
      <div className="card login-card">
        <div className="login-logo">
          <div className="login-logo-badge" style={{ background: branding.cor_primaria }}>
            {firstLetter}
          </div>
          <h1 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 4px" }}>
            {branding.tenant_name}
          </h1>
          <p style={{ fontSize: 13, color: "var(--color-text-muted)", margin: 0 }}>
            Dashboard Administrativo
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              className="input"
              placeholder="seu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Senha</label>
            <input
              id="password"
              type="password"
              className="input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          <button
            id="btn-login"
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: "100%", marginTop: 8, padding: "12px" }}
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>

        <p style={{ textAlign: "center", marginTop: 24, fontSize: 12, color: "var(--color-text-muted)" }}>
          Atendê Platform v2.0 — Multi-tenant
        </p>
      </div>
    </div>
  );
}
