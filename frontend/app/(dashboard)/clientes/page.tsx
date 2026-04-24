"use client";

import { useState } from "react";
import { RefreshCw, Users, MapPin, ShoppingCart, Ban, CheckCircle } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { customersApi } from "@/lib/api";
import { formatPhone } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Customer } from "@/lib/types";

export default function ClientesPage() {
  const { data: customers, loading, reload } = useApi<Customer[]>(
    () => customersApi.list(100),
    []
  );

  const [toggling, setToggling] = useState<string | null>(null);

  async function toggleBlock(customer: Customer) {
    const action = customer.is_blocked ? "Desbloquear" : "Bloquear";
    if (!confirm(`${action} este cliente?`)) return;
    setToggling(customer.id);
    try {
      await customersApi.toggleBlock(customer.id, !customer.is_blocked);
      reload();
    } finally {
      setToggling(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
          <p className="text-sm text-gray-500">{customers?.length ?? 0} cliente(s)</p>
        </div>
        <Button variant="outline" size="sm" onClick={reload} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* Content */}
      {loading ? (
        <p className="text-sm text-gray-400">Carregando clientes...</p>
      ) : !customers?.length ? (
        <Card>
          <CardContent className="py-12 text-center text-gray-400">
            <Users className="mx-auto mb-3 h-10 w-10 opacity-30" />
            <p>Nenhum cliente cadastrado.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {customers.map((customer) => (
            <Card key={customer.id} className={customer.is_blocked ? "opacity-60" : ""}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    {/* Name / phone */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-gray-900 truncate">
                        {customer.name ?? formatPhone(customer.phone)}
                      </span>
                      {customer.is_blocked && (
                        <Badge variant="destructive" className="text-xs">Bloqueado</Badge>
                      )}
                    </div>

                    {customer.name && (
                      <p className="text-xs text-gray-400 mt-0.5">{formatPhone(customer.phone)}</p>
                    )}

                    {/* Address */}
                    {customer.building_block && (
                      <p className="mt-1.5 flex items-center gap-1 text-xs text-gray-500">
                        <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
                        Bloco {customer.building_block}, Apto {customer.apartment}
                      </p>
                    )}

                    {/* Orders count */}
                    <p className="mt-1 flex items-center gap-1 text-xs text-gray-400">
                      <ShoppingCart className="h-3.5 w-3.5 flex-shrink-0" />
                      {customer.total_orders} pedido(s)
                    </p>
                  </div>

                  {/* Block/unblock action */}
                  <Button
                    size="sm"
                    variant="outline"
                    className={
                      customer.is_blocked
                        ? "text-green-600 hover:border-green-300 hover:bg-green-50"
                        : "text-red-600 hover:border-red-300 hover:bg-red-50"
                    }
                    onClick={() => toggleBlock(customer)}
                    disabled={toggling === customer.id}
                    title={customer.is_blocked ? "Desbloquear" : "Bloquear"}
                  >
                    {customer.is_blocked ? (
                      <CheckCircle className="h-4 w-4" />
                    ) : (
                      <Ban className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
