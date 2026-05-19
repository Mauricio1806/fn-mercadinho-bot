/**
 * Página de produtos com upload CSV para importação de catálogo.
 */

import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getProducts, importCSV } from "@/lib/api";
import { getTenantId } from "@/lib/auth";
import { Upload, Package } from "lucide-react";
import toast from "react-hot-toast";

export function Products() {
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const tenantId = getTenantId();

  const { data: products = [], isLoading } = useQuery({
    queryKey: ["products"],
    queryFn: getProducts,
  });

  async function handleCSVUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !tenantId) return;

    setImporting(true);
    try {
      const result = await importCSV(tenantId, file);
      toast.success(
        `✅ Importado! ${result.created} criados, ${result.updated} atualizados.`
      );
      if (result.errors?.length) {
        toast.error(`⚠️ ${result.errors.length} erro(s). Verifique o arquivo.`);
      }
      qc.invalidateQueries({ queryKey: ["products"] });
    } catch {
      toast.error("Falhou ao importar CSV.");
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  const fmtCurrency = (n: number) =>
    n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Produtos</h1>
          <p className="page-subtitle">Catálogo de produtos do seu negócio</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            ref={fileInputRef}
            id="csv-file-input"
            type="file"
            accept=".csv,.txt"
            style={{ display: "none" }}
            onChange={handleCSVUpload}
          />
          <button
            id="btn-import-csv"
            className="btn btn-ghost"
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
          >
            <Upload size={15} />
            {importing ? "Importando..." : "Importar CSV"}
          </button>
        </div>
      </div>

      {/* Dica CSV */}
      <div className="card" style={{ marginBottom: 16, padding: "12px 16px",
        background: "rgba(var(--color-primary), 0.05)",
        borderColor: "rgba(59,130,246,0.2)" }}>
        <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
          <strong style={{ color: "var(--color-text)" }}>Formato CSV:</strong>{" "}
          <code style={{ background: "rgba(255,255,255,0.06)", padding: "1px 6px", borderRadius: 4 }}>
            nome,preco,categoria,disponivel,external_id
          </code>
          {" "}— O campo <code>external_id</code> é usado para deduplicação (upsert).
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrapper" style={{ border: "none", borderRadius: "14px" }}>
          <table>
            <thead>
              <tr>
                <th>Produto</th>
                <th>Categoria</th>
                <th>Preço</th>
                <th>Estoque</th>
                <th>Status</th>
                <th>Fonte</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={6} style={{ textAlign: "center", padding: 32, color: "var(--color-text-muted)" }}>Carregando...</td></tr>
              ) : !products.length ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: 48 }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                      <Package size={40} style={{ color: "var(--color-text-muted)", opacity: 0.4 }} />
                      <div style={{ color: "var(--color-text-muted)" }}>
                        Nenhum produto ainda.<br />
                        <button className="btn btn-primary" style={{ marginTop: 12 }}
                          onClick={() => fileInputRef.current?.click()}>
                          Importar catálogo CSV
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
              ) : (
                products.map((p: any) => (
                  <tr key={p.id}>
                    <td style={{ fontWeight: 500 }}>{p.name}</td>
                    <td style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                      {p.category_id?.toString().slice(0, 8)}
                    </td>
                    <td style={{ fontWeight: 600 }}>{fmtCurrency(p.price)}</td>
                    <td style={{ fontSize: 12 }}>
                      {p.stock_quantity != null ? p.stock_quantity : "∞"}
                    </td>
                    <td>
                      <span className={`badge ${p.is_available && p.in_stock ? "badge-delivered" : "badge-cancelled"}`}>
                        {p.is_available && p.in_stock ? "Disponível" : "Indisponível"}
                      </span>
                    </td>
                    <td style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
                      {p.external_source ?? "manual"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
