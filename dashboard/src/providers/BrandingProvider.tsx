/**
 * BrandingProvider — injeta CSS variables do tenant via JWT.
 *
 * Lê o campo branding do JWT e define as CSS variables globais,
 * permitindo que toda a interface mude de cor por tenant automaticamente.
 */

import { createContext, useContext, useEffect, type ReactNode } from "react";
import { getBranding } from "@/lib/auth";

interface BrandingContextValue {
  tenantName: string;
  corPrimaria: string;
  corSecundaria: string;
  logoUrl: string | null;
}

const BrandingContext = createContext<BrandingContextValue>({
  tenantName: "Atendê Platform",
  corPrimaria: "#1976D2",
  corSecundaria: "#FFC107",
  logoUrl: null,
});

export function BrandingProvider({ children }: { children: ReactNode }) {
  const branding = getBranding();

  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--color-primary", branding.cor_primaria);
    root.style.setProperty("--color-secondary", branding.cor_secundaria);

    // Gera versão mais clara e mais escura da cor primária para hover states
    root.style.setProperty("--color-primary-light", `${branding.cor_primaria}33`);
    root.style.setProperty("--color-primary-dark", branding.cor_primaria);

    // Atualiza o título da aba
    document.title = `${branding.tenant_name} — Dashboard`;
  }, [branding.cor_primaria, branding.cor_secundaria, branding.tenant_name]);

  return (
    <BrandingContext.Provider
      value={{
        tenantName: branding.tenant_name,
        corPrimaria: branding.cor_primaria,
        corSecundaria: branding.cor_secundaria,
        logoUrl: branding.logo_url,
      }}
    >
      {children}
    </BrandingContext.Provider>
  );
}

export function useBranding(): BrandingContextValue {
  return useContext(BrandingContext);
}
