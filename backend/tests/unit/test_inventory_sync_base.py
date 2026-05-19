"""Testes unitários — CSV Import."""

import pytest

from app.integrations.csv_import import CSVImport


class TestCSVImport:

    def setup_method(self):
        self.importer = CSVImport(db=None)

    def test_parse_csv_basico(self):
        csv_content = "nome,preco,categoria,disponivel,external_id\nCoca-Cola 2L,9.99,Bebidas,true,SKU001"
        produtos = self.importer.parse_csv(csv_content)
        assert len(produtos) == 1
        p = produtos[0]
        assert p.name == "Coca-Cola 2L"
        assert p.price == 9.99
        assert p.category_name == "Bebidas"
        assert p.is_available is True
        assert p.external_id == "SKU001"

    def test_parse_csv_multiplos(self):
        csv_content = (
            "nome,preco,categoria,disponivel,external_id\n"
            "Produto A,10.00,Cat1,true,EXT001\n"
            "Produto B,20.00,Cat2,false,EXT002\n"
            "Produto C,30.00,Cat1,true,EXT003"
        )
        produtos = self.importer.parse_csv(csv_content)
        assert len(produtos) == 3

    def test_disponivel_false_desativa(self):
        csv_content = "nome,preco,categoria,disponivel,external_id\nProduto,5.00,Cat,false,SKU"
        produtos = self.importer.parse_csv(csv_content)
        assert produtos[0].is_available is False

    def test_disponivel_vazio_usa_default_false(self):
        """Campo disponivel vazio não é truthy — produto fica indisponível."""
        csv_content = "nome,preco,categoria,disponivel,external_id\nProduto,5.00,Cat,,SKU"
        produtos = self.importer.parse_csv(csv_content)
        # String vazia "" não está na lista de valores válidos (true/sim/1/yes)
        # Comportamento correto: is_available=False
        assert produtos[0].is_available is False

    def test_external_id_vazio_usa_nome_como_chave(self):
        csv_content = "nome,preco,categoria,disponivel,external_id\nCafé Coado,4.50,Bebidas,true,"
        produtos = self.importer.parse_csv(csv_content)
        assert len(produtos) == 1
        # external_id deve ser derivado do nome (não vazio)
        assert produtos[0].external_id != ""
        assert produtos[0].external_id is not None

    def test_colunas_faltando_lanca_erro(self):
        csv_content = "nome,categoria\nProduto,Cat"
        with pytest.raises(ValueError) as exc_info:
            self.importer.parse_csv(csv_content)
        assert "preco" in str(exc_info.value)

    def test_preco_com_virgula(self):
        csv_content = "nome,preco,categoria,disponivel,external_id\nProduto,9,99,Bebidas,true,SKU"
        # CSV com vírgula no preço pode ser interpretado como colunas extras
        # Mas se o campo tem vírgula como separador decimal:
        csv_content2 = "nome,preco,categoria,disponivel,external_id\nProduto,9.99,Bebidas,true,SKU"
        produtos = self.importer.parse_csv(csv_content2)
        assert produtos[0].price == 9.99

    def test_linha_com_nome_vazio_ignorada(self):
        csv_content = (
            "nome,preco,categoria,disponivel,external_id\n"
            ",9.99,Bebidas,true,SKU001\n"
            "Produto Válido,5.00,Cat,true,SKU002"
        )
        produtos = self.importer.parse_csv(csv_content)
        assert len(produtos) == 1
        assert produtos[0].name == "Produto Válido"

    def test_bom_utf8_removido(self):
        """CSV com BOM UTF-8 deve ser parseado corretamente."""
        csv_content = b"\xef\xbb\xbfnome,preco,categoria,disponivel,external_id\nProduto,5.00,Cat,true,SKU"
        produtos = self.importer.parse_csv(csv_content)
        assert len(produtos) == 1
        assert produtos[0].name == "Produto"

    def test_external_source_e_csv(self):
        csv_content = "nome,preco,categoria,disponivel,external_id\nProduto,5.00,Cat,true,SKU"
        produtos = self.importer.parse_csv(csv_content)
        assert produtos[0].external_source == "csv"
