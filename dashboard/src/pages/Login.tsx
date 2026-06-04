/**
 * Login — visual profissional com fundo desfocado dinâmico por tenant.
 * Igual ao padrão Awsales: background blurred + card centralizado.
 */

import { useState, type FormEvent } from "react";
import { saveTokens, getBranding } from "@/lib/auth";
import { login as apiLogin } from "@/lib/api";
import toast from "react-hot-toast";

interface LoginProps {
  onSuccess: () => void;
}

export function Login({ onSuccess }: LoginProps) {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading]   = useState(false);
  const [showPass, setShowPass] = useState(false);
  const branding = getBranding();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email || !password) return;
    setLoading(true);
    try {
      const { access_token, refresh_token } = await apiLogin(email, password);
      saveTokens(access_token, refresh_token);
      onSuccess();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Email ou senha incorretos.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-root">
      {/* Fundo desfocado — mockup do dashboard */}
      <div className="login-bg">
        <div className="login-bg-mockup">
          <div className="mockup-sidebar" style={{ background: branding.cor_primaria + "22" }} />
          <div className="mockup-content">
            {[120, 80, 160, 100, 140, 90].map((w, i) => (
              <div key={i} className="mockup-bar" style={{
                width: w,
                height: 12 + (i % 3) * 6,
                background: i % 2 === 0 ? branding.cor_primaria + "44" : "#ffffff11"
              }} />
            ))}
            {[1,2,3].map(i => (
              <div key={i} className="mockup-card" style={{ background: "#ffffff08" }}>
                <div className="mockup-line" style={{ width: "60%", background: branding.cor_primaria + "33" }} />
                <div className="mockup-line" style={{ width: "40%", background: "#ffffff11" }} />
                <div className="mockup-line" style={{ width: "80%", background: "#ffffff0a" }} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Overlay desfocado */}
      <div className="login-overlay" />

      {/* Card de login */}
      <div className="login-card-wrap">
        <div className="login-card">
          {/* Logo / ícone */}
          <div className="login-brand">
            {branding.logo_url ? (
              <img
                src={branding.logo_url}
                alt={branding.tenant_name}
                className="login-logo-img"
              />
            ) : (
              <div
                className="login-logo-icon"
                style={{ background: branding.cor_primaria }}
              >
                {branding.tenant_name.charAt(0).toUpperCase()}
              </div>
            )}
            <h1 className="login-title">{branding.tenant_name}</h1>
            <p className="login-subtitle">Painel administrativo</p>
          </div>

          {/* Formulário */}
          <form onSubmit={handleSubmit} className="login-form">
            <div className="login-field">
              <label htmlFor="email" className="login-label">E-mail</label>
              <input
                id="email"
                type="email"
                className="login-input"
                placeholder="seu@email.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoFocus
                autoComplete="email"
              />
            </div>

            <div className="login-field">
              <label htmlFor="password" className="login-label">Senha</label>
              <div className="login-input-wrap">
                <input
                  id="password"
                  type={showPass ? "text" : "password"}
                  className="login-input"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="login-eye"
                  onClick={() => setShowPass(v => !v)}
                  tabIndex={-1}
                >
                  {showPass ? "🙈" : "👁"}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="login-btn"
              disabled={loading}
              style={{ background: branding.cor_primaria }}
            >
              {loading ? (
                <span className="login-spinner" />
              ) : "Entrar"}
            </button>
          </form>

          <p className="login-footer">
            Atendê Platform · Acesso seguro
          </p>
        </div>
      </div>
    </div>
  );
}
