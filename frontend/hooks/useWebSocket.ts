"use client";

import { useEffect, useRef, useCallback } from "react";

type MessageHandler = (data: unknown) => void;

interface UseWebSocketOptions {
  /** Identificador da conversa. Passa null para desconectar. */
  conversationId: string | null;
  onMessage: MessageHandler;
  /** Intervalo de ping em ms (padrão: 25 000) */
  pingInterval?: number;
}

/**
 * Conecta a ws://{host}/ws/conversations/{id}?token={jwt}
 * Reconecta automaticamente se a conexão cair (até 5 tentativas).
 */
export function useWebSocket({
  conversationId,
  onMessage,
  pingInterval = 25_000,
}: UseWebSocketOptions): void {
  const wsRef = useRef<WebSocket | null>(null);
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const retriesRef = useRef(0);
  const MAX_RETRIES = 5;

  const connect = useCallback(() => {
    if (!conversationId) return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const apiHost =
      process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:\/\//, "") ??
      "localhost:8000";
    const url = `${protocol}://${apiHost}/ws/conversations/${conversationId}?token=${token}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      retriesRef.current = 0;
      // Inicia heartbeat
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, pingInterval);
    };

    ws.onmessage = (event) => {
      if (event.data === "pong") return;
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch {
        // mensagem não-JSON ignorada
      }
    };

    ws.onclose = (event) => {
      if (pingRef.current) clearInterval(pingRef.current);
      // Reconecta se não foi fechamento intencional e ainda há retries
      if (event.code !== 1000 && retriesRef.current < MAX_RETRIES) {
        retriesRef.current += 1;
        const delay = Math.min(1000 * 2 ** retriesRef.current, 30_000);
        setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [conversationId, onMessage, pingInterval]);

  useEffect(() => {
    // Fecha conexão anterior e abre nova
    wsRef.current?.close(1000, "conversa trocada");
    if (pingRef.current) clearInterval(pingRef.current);
    retriesRef.current = 0;

    if (conversationId) connect();

    return () => {
      wsRef.current?.close(1000, "unmount");
      if (pingRef.current) clearInterval(pingRef.current);
    };
  }, [conversationId, connect]);
}
