"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { MessageSquare, User, RefreshCw, UserCheck, Wifi, WifiOff } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { useWebSocket } from "@/hooks/useWebSocket";
import { conversationsApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Conversation, Message, ConversationState } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATE_LABEL: Record<ConversationState, string> = {
  greeting: "Saudação",
  main_menu: "Menu",
  order_items: "Pedido",
  order_confirm: "Confirmando",
  order_delivery: "Delivery",
  order_payment: "Aguard. PIX",
  payment_receipt: "Aguard. comprovante",
  delivery_info: "Info delivery",
  hours_info: "Horário",
  free_chat: "Livre",
  closed: "Encerrado",
};

interface WsNewMessage {
  type: "new_message";
  data: {
    direction: "inbound" | "outbound";
    content: string;
    is_ai_generated: boolean;
    tokens_used: number | null;
  };
}

export default function ConversasPage() {
  const [selected, setSelected] = useState<string | null>(null);
  const [takingOver, setTakingOver] = useState(false);
  const [liveMessages, setLiveMessages] = useState<Message[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: conversations, loading, reload } = useApi(
    () => conversationsApi.list(50),
    []
  );

  const { data: historicMessages, loading: msgsLoading } = useApi<Message[]>(
    () => (selected ? conversationsApi.getMessages(selected) : Promise.resolve([])),
    [selected]
  );

  // Reseta mensagens ao vivo quando troca de conversa
  useEffect(() => {
    setLiveMessages([]);
    setWsConnected(false);
  }, [selected]);

  // Scroll automático ao receber nova mensagem
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [liveMessages, historicMessages]);

  const handleWsMessage = useCallback((raw: unknown) => {
    const msg = raw as WsNewMessage;
    if (msg.type !== "new_message") return;

    setWsConnected(true);
    setLiveMessages((prev) => [
      ...prev,
      {
        id: `live-${Date.now()}`,
        direction: msg.data.direction,
        content: msg.data.content,
        is_ai_generated: msg.data.is_ai_generated,
        tokens_used: msg.data.tokens_used,
      },
    ]);

    // Atualiza contagem na lista lateral
    reload();
  }, [reload]);

  useWebSocket({ conversationId: selected, onMessage: handleWsMessage });

  async function handleTakeover() {
    if (!selected || !confirm("Assumir esta conversa? O bot não responderá mais.")) return;
    setTakingOver(true);
    try {
      await conversationsApi.takeover(selected);
      reload();
    } finally {
      setTakingOver(false);
    }
  }

  const selectedConv = conversations?.find((c) => c.id === selected);

  // Mensagens históricas + ao vivo (sem duplicatas simples)
  const allMessages = [
    ...(historicMessages ?? []),
    ...liveMessages,
  ];

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-6">
      {/* Left: conversation list */}
      <div className="w-72 flex-shrink-0">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Conversas</h1>
          <Button variant="outline" size="icon" onClick={reload} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>

        <div className="space-y-1.5 overflow-y-auto">
          {loading ? (
            <p className="text-sm text-gray-400 px-2">Carregando...</p>
          ) : conversations?.length === 0 ? (
            <p className="text-sm text-gray-400 px-2">Nenhuma conversa.</p>
          ) : (
            conversations?.map((conv) => (
              <button
                key={conv.id}
                onClick={() => setSelected(conv.id)}
                className={cn(
                  "w-full rounded-lg border p-3 text-left transition-colors",
                  selected === conv.id
                    ? "border-green-300 bg-green-50"
                    : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50"
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <User className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {conv.customer_name || conv.customer_phone || conv.customer_id.slice(0, 8).toUpperCase()}
                      </p>
                      {conv.customer_phone && conv.customer_name && (
                        <p className="text-xs text-gray-400 truncate">{conv.customer_phone}</p>
                      )}
                    </div>
                  </div>
                  <Badge
                    variant={
                      conv.status === "active"
                        ? "success"
                        : conv.status === "human"
                        ? "warning"
                        : "outline"
                    }
                    className="flex-shrink-0"
                  >
                    {conv.status === "active" ? "ativo" : conv.status === "human" ? "humano" : conv.status === "closed" ? "fechado" : conv.status}
                  </Badge>
                </div>
                <div className="mt-1 flex items-center justify-between gap-2">
                  <span className="text-xs text-gray-500 truncate">{STATE_LABEL[conv.state]}</span>
                  <span className="text-xs text-gray-400 flex-shrink-0">{conv.message_count} msgs</span>
                </div>
                {conv.last_message && (
                  <p className="mt-1 text-xs text-gray-400 truncate">{conv.last_message}</p>
                )}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Right: messages */}
      <div className="flex-1 flex flex-col">
        {!selected ? (
          <div className="flex flex-1 flex-col items-center justify-center text-gray-400">
            <MessageSquare className="h-12 w-12 opacity-20 mb-3" />
            <p>Selecione uma conversa</p>
          </div>
        ) : (
          <Card className="flex flex-1 flex-col overflow-hidden">
            <CardHeader className="border-b pb-3 flex-row items-center justify-between space-y-0">
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle className="text-sm">
                    {selectedConv?.customer_name || selectedConv?.customer_phone || selected.slice(0, 8).toUpperCase()}
                  </CardTitle>
                  {/* Indicador WebSocket */}
                  {wsConnected ? (
                    <span className="flex items-center gap-1 text-xs text-green-600">
                      <Wifi className="h-3 w-3" /> ao vivo
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs text-gray-400">
                      <WifiOff className="h-3 w-3" /> conectando...
                    </span>
                  )}
                </div>
                {selectedConv && (
                  <p className="text-xs text-gray-500 mt-0.5">
                    Estado: {STATE_LABEL[selectedConv.state]} • {selectedConv.message_count} mensagens
                  </p>
                )}
              </div>
              {selectedConv?.status === "active" && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleTakeover}
                  disabled={takingOver}
                >
                  <UserCheck className="h-4 w-4 mr-1.5" />
                  Assumir
                </Button>
              )}
            </CardHeader>

            <CardContent className="flex-1 overflow-y-auto p-4 space-y-3">
              {msgsLoading ? (
                <p className="text-sm text-gray-400">Carregando mensagens...</p>
              ) : allMessages.length === 0 ? (
                <p className="text-sm text-gray-400">Sem mensagens.</p>
              ) : (
                allMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={cn(
                      "flex",
                      msg.direction === "outbound" ? "justify-end" : "justify-start"
                    )}
                  >
                    <div
                      className={cn(
                        "max-w-[75%] rounded-2xl px-4 py-2 text-sm",
                        msg.direction === "outbound"
                          ? "bg-green-700 text-white rounded-br-sm"
                          : "bg-gray-100 text-gray-900 rounded-bl-sm"
                      )}
                    >
                      <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                      {msg.is_ai_generated && msg.tokens_used && (
                        <p className="mt-1 text-[10px] opacity-60">{msg.tokens_used} tokens</p>
                      )}
                    </div>
                  </div>
                ))
              )}
              <div ref={bottomRef} />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
