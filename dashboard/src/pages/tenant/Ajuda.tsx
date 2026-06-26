import { MessageCircle, Phone } from "lucide-react";

const WHATSAPP_URL = "https://wa.me/5571988133151";
const WHATSAPP_DISPLAY = "+55 71 98813-3151";

export function Ajuda() {
  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Ajuda</h1>
          <p className="page-subtitle">Como funciona o Mercazap e onde tirar dúvidas</p>
        </div>
      </div>

      <div className="card" style={{ padding: 20, maxWidth: 720, marginTop: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginTop: 0 }}>Como funciona</h2>
        <p style={{ fontSize: 13.5, lineHeight: 1.7, color: "var(--color-text)" }}>
          O Mercazap é um bot de WhatsApp que atende seus clientes automaticamente.
          Recebe pedidos, calcula frete, gera o Pix, confirma o pagamento e avisa
          quando o pedido sai pra entrega — tudo na mesma conversa do WhatsApp.
        </p>
      </div>

      <div className="card" style={{ padding: 20, maxWidth: 720, marginTop: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginTop: 0 }}>O que tem em cada página</h2>
        <ul style={{ paddingLeft: 20, fontSize: 13.5, lineHeight: 1.9, color: "var(--color-text)" }}>
          <li><strong>Dashboard</strong>: resumo do dia, gráfico semanal e últimos pedidos</li>
          <li><strong>Pedidos</strong>: lista filtrável; mudar status notifica o cliente no WhatsApp</li>
          <li><strong>Conversas</strong>: histórico do bot; "Assumir" pausa o bot</li>
          <li><strong>Produtos</strong>: catálogo (CSV, Bling, Tiny ou webhook)</li>
          <li><strong>Clientes</strong>: cadastro, notas internas, bloqueio</li>
          <li><strong>Configurações</strong>: Pix, horário, delivery, persona, branding</li>
        </ul>
      </div>

      <div className="card" style={{ padding: 20, maxWidth: 720, marginTop: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginTop: 0 }}>Antes de começar a vender</h2>
        <p style={{ fontSize: 13.5, marginBottom: 8 }}>
          Em <strong>Configurações</strong>, preencha pelo menos:
        </p>
        <ul style={{ paddingLeft: 20, fontSize: 13, lineHeight: 1.8, color: "var(--color-text-muted)" }}>
          <li>Negócio: nome, endereço, telefones dos donos</li>
          <li>Pix: chave e titular</li>
          <li>Horário: quando aceitar pedidos</li>
          <li>Delivery: taxas e raio</li>
        </ul>
      </div>

      <div className="card" style={{ padding: 20, maxWidth: 720, marginTop: 16, borderColor: "var(--color-primary)" }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginTop: 0, color: "var(--color-primary)", display: "flex", alignItems: "center", gap: 8 }}>
          <MessageCircle size={18} />
          Ficou com dúvida?
        </h2>
        <p style={{ fontSize: 13.5, marginBottom: 12 }}>
          Mauricio responde direto no WhatsApp. Manda dúvida, bug, sugestão ou pedido de configuração.
        </p>
        <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="btn btn-primary" style={{ textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 8 }}>
          <Phone size={14} />
          {WHATSAPP_DISPLAY}
        </a>
      </div>
    </div>
  );
}
