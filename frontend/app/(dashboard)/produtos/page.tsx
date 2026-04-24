"use client";

import { useState } from "react";
import { RefreshCw, Package, ToggleLeft, ToggleRight, Pencil, Check, X } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { productsApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import type { ProductCategory, Product } from "@/lib/types";

export default function ProdutosPage() {
  const { data: categories, loading, reload } = useApi<ProductCategory[]>(
    () => productsApi.listCategories(),
    []
  );

  const [toggling, setToggling] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [editPrice, setEditPrice] = useState("");
  const [saving, setSaving] = useState(false);

  const totalProducts = categories?.reduce((sum, c) => sum + c.products.length, 0) ?? 0;

  async function toggleAvailability(product: Product) {
    setToggling(product.id);
    try {
      await productsApi.updateProduct(product.id, { is_available: !product.is_available });
      reload();
    } finally {
      setToggling(null);
    }
  }

  function startEdit(product: Product) {
    setEditing(product.id);
    setEditPrice(product.price.toFixed(2));
  }

  function cancelEdit() {
    setEditing(null);
    setEditPrice("");
  }

  async function savePrice(product: Product) {
    const price = parseFloat(editPrice.replace(",", "."));
    if (isNaN(price) || price <= 0) return;
    setSaving(true);
    try {
      await productsApi.updateProduct(product.id, { price });
      reload();
      setEditing(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Produtos</h1>
          <p className="text-sm text-gray-500">{totalProducts} produto(s)</p>
        </div>
        <Button variant="outline" size="sm" onClick={reload} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* Content */}
      {loading ? (
        <p className="text-sm text-gray-400">Carregando produtos...</p>
      ) : !categories?.length ? (
        <Card>
          <CardContent className="py-12 text-center text-gray-400">
            <Package className="mx-auto mb-3 h-10 w-10 opacity-30" />
            <p>Nenhum produto cadastrado.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {categories.map((category) => (
            <div key={category.id}>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
                {category.name}
              </h2>
              <div className="grid gap-2">
                {category.products.map((product) => (
                  <Card key={product.id}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between gap-4">
                        {/* Product info */}
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">{product.name}</span>
                            {!product.is_available && (
                              <Badge variant="outline" className="text-xs text-gray-400">
                                Indisponível
                              </Badge>
                            )}
                          </div>
                          {product.description && (
                            <p className="mt-0.5 text-xs text-gray-400">{product.description}</p>
                          )}
                        </div>

                        {/* Price */}
                        <div className="w-32">
                          {editing === product.id ? (
                            <div className="flex items-center gap-1">
                              <span className="text-sm text-gray-500">R$</span>
                              <Input
                                className="h-7 w-20 px-2 text-sm"
                                value={editPrice}
                                onChange={(e) => setEditPrice(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") savePrice(product);
                                  if (e.key === "Escape") cancelEdit();
                                }}
                                autoFocus
                              />
                            </div>
                          ) : (
                            <span className="text-sm font-semibold text-gray-900">
                              {formatCurrency(product.price)}
                            </span>
                          )}
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-1">
                          {editing === product.id ? (
                            <>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-7 w-7 text-green-600 hover:text-green-700"
                                onClick={() => savePrice(product)}
                                disabled={saving}
                              >
                                <Check className="h-4 w-4" />
                              </Button>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-7 w-7 text-gray-400 hover:text-gray-600"
                                onClick={cancelEdit}
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </>
                          ) : (
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-7 w-7 text-gray-400 hover:text-gray-600"
                              onClick={() => startEdit(product)}
                            >
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                          )}

                          <Button
                            size="icon"
                            variant="ghost"
                            className={`h-7 w-7 ${
                              product.is_available
                                ? "text-green-600 hover:text-green-700"
                                : "text-gray-400 hover:text-gray-600"
                            }`}
                            onClick={() => toggleAvailability(product)}
                            disabled={toggling === product.id}
                            title={product.is_available ? "Desativar" : "Ativar"}
                          >
                            {product.is_available ? (
                              <ToggleRight className="h-5 w-5" />
                            ) : (
                              <ToggleLeft className="h-5 w-5" />
                            )}
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
