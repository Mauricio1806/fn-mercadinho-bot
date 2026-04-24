"""
Parse estoque.md → config/catalog_full.yaml

Formato do estoque:
  ## PRECO CODIGO DESCRICAO CATEGORIA UNIT QUANTIDADE

Executar:
  python parse_estoque.py [caminho_estoque.md] [saida_catalog_full.yaml]

Padrões:
  - Preço: número decimal com vírgula (ex: 11,69)
  - Código: sequência de dígitos (barcode ou código interno)
  - Categoria: palavra-chave conhecida (BEBIDAS, FLV HORTI, etc.)
  - Unidade: UN ou KG (imediatamente após categoria)
  - Quantidade: número decimal negativo ou positivo (estoque atual)
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

# Categorias conhecidas, em ordem de comprimento decrescente para match mais específico primeiro
CATEGORIAS_CONHECIDAS = [
    "FRIOS E LATICÍNIOS",
    "FRIOS E LATICINIOS",
    "CUIDADOS PESSOAIS",
    "UTLIDADES DOMESTICAS",
    "UTILIDADES DOMESTICAS",
    "HORTIFRUTTI",
    "ALMOXARIFADO",
    "CONGELADOS",
    "BOMBONIERE",
    "CONSERVAS",
    "BISCOITOS",
    "LATICINIOS",
    "LATICÍNIOS",
    "FLV HORTI",
    "MATINAIS",
    "AÇOUGUE",
    "ACOUGUE",
    "LIMPEZA",
    "CEREAIS",
    "BEBIDAS",
    "HIGIENE",
    "GERAL",
]

# Mapeamento para nomes legíveis
CATEGORIA_MAP = {
    "FRIOS E LATICÍNIOS": "Frios e Laticínios",
    "FRIOS E LATICINIOS": "Frios e Laticínios",
    "CUIDADOS PESSOAIS": "Cuidados Pessoais",
    "UTLIDADES DOMESTICAS": "Utilidades Domésticas",
    "UTILIDADES DOMESTICAS": "Utilidades Domésticas",
    "HORTIFRUTTI": "FLV / Horti",
    "ALMOXARIFADO": "Almoxarifado",
    "CONGELADOS": "Congelados",
    "BOMBONIERE": "Bomboniere",
    "CONSERVAS": "Conservas",
    "BISCOITOS": "Biscoitos",
    "LATICINIOS": "Frios e Laticínios",
    "LATICÍNIOS": "Frios e Laticínios",
    "FLV HORTI": "FLV / Horti",
    "MATINAIS": "Cereais e Matinais",
    "AÇOUGUE": "Açougue",
    "ACOUGUE": "Açougue",
    "LIMPEZA": "Limpeza",
    "CEREAIS": "Cereais e Matinais",
    "BEBIDAS": "Bebidas",
    "HIGIENE": "Higiene / Cuidados Pessoais",
    "GERAL": "Geral",
}

# Regex para linha do estoque
# Formato: ## PRECO CODIGO_DIGITOS DESCRICAO CATEGORIA UNIT QUANTIDADE
LINE_RE = re.compile(
    r"^##\s*"
    r"(?P<preco>\d+[.,]\d{2})"          # preço: dígitos,2decimais
    r"(?P<codigo>\d+)"                   # código: dígitos
    r"(?P<resto>.+)$"                    # resto: descrição+categoria+un+qtd
)

UNIT_RE = re.compile(r"(UN|KG)(-?\d+[.,]\d+)$")


def _find_category(texto: str) -> tuple[str | None, int, int]:
    """Retorna (categoria_raw, inicio, fim) ou (None, -1, -1)."""
    texto_upper = texto.upper()
    for cat in CATEGORIAS_CONHECIDAS:
        idx = texto_upper.find(cat)
        if idx >= 0:
            return cat, idx, idx + len(cat)
    return None, -1, -1


def _normalize_price(preco_str: str) -> float:
    return float(preco_str.replace(",", "."))


def _title_case_product(name: str) -> str:
    """Converte NOME EM CAPS para Nome Em Caps (título)."""
    stop_words = {"DE", "DA", "DO", "DAS", "DOS", "E", "A", "O", "EM", "COM", "POR", "PARA"}
    words = name.strip().split()
    result = []
    for i, w in enumerate(words):
        if i == 0 or w not in stop_words:
            result.append(w.capitalize())
        else:
            result.append(w.lower())
    return " ".join(result)


def parse_line(line: str) -> dict | None:
    """Parseia uma linha do estoque e retorna dict {nome, preco, categoria, unidade, qtd}."""
    line = line.strip()
    if not line.startswith("##"):
        return None

    m = LINE_RE.match(line)
    if not m:
        return None

    preco_str = m.group("preco")
    resto = m.group("resto").strip()

    # Encontra categoria no resto
    cat_raw, cat_start, cat_end = _find_category(resto)
    if cat_raw is None:
        return None

    descricao_raw = resto[:cat_start].strip()
    apos_cat = resto[cat_end:].strip()

    # Extrai unidade e quantidade do que vem após a categoria
    unit_match = UNIT_RE.search(apos_cat)
    if not unit_match:
        return None

    unidade = unit_match.group(1)
    # qtd_str = unit_match.group(2)  # estoque (negativo = deve)

    if not descricao_raw:
        return None

    try:
        preco = _normalize_price(preco_str)
    except ValueError:
        return None

    categoria_legivel = CATEGORIA_MAP.get(cat_raw, cat_raw.title())
    nome_produto = _title_case_product(descricao_raw)

    return {
        "nome": nome_produto,
        "preco": round(preco, 2),
        "categoria": categoria_legivel,
        "unidade": unidade,
    }


def parse_estoque(filepath: str) -> dict[str, list[dict]]:
    """Lê o arquivo estoque.md e retorna {categoria: [produtos]}."""
    catalog: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()  # (categoria, nome) para deduplicação

    with open(filepath, encoding="utf-8", errors="ignore") as f:
        for line in f:
            product = parse_line(line)
            if not product:
                continue

            key = (product["categoria"], product["nome"].upper())
            if key in seen:
                continue
            seen.add(key)

            cat = product.pop("categoria")
            catalog[cat].append(product)

    return dict(catalog)


def to_yaml_structure(catalog: dict[str, list[dict]]) -> list[dict]:
    """Converte para estrutura compatível com business.yaml/catalog_full.yaml."""
    result = []
    for categoria, produtos in sorted(catalog.items()):
        produtos_sorted = sorted(produtos, key=lambda p: p["nome"])
        result.append({
            "categoria": categoria,
            "produtos": produtos_sorted,
        })
    return result


def main() -> None:
    estoque_path = sys.argv[1] if len(sys.argv) > 1 else "../../estoque.md"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "../../config/catalog_full.yaml"

    estoque_file = Path(estoque_path)
    output_file = Path(output_path)

    if not estoque_file.exists():
        print(f"Arquivo não encontrado: {estoque_file}")
        sys.exit(1)

    print(f"Lendo {estoque_file}...")
    catalog = parse_estoque(str(estoque_file))

    total_produtos = sum(len(p) for p in catalog.values())
    print(f"Encontrados: {total_produtos} produtos em {len(catalog)} categorias")

    for cat, prods in sorted(catalog.items()):
        print(f"  {cat}: {len(prods)} produtos")

    structure = to_yaml_structure(catalog)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(
            structure,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

    print(f"\nCatálogo salvo em: {output_file}")
    print("Execute 'make seed' para popular o banco de dados.")


if __name__ == "__main__":
    main()
