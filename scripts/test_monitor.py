"""Testes locais do extrator; não acessam a rede."""
import unittest
import monitor


class MonitorTests(unittest.TestCase):
    AGRO = {
        "id": "agropolos",
        "url": "https://institutoagropolos.org.br/editais/",
        "kind": "agropolos",
        "name": "Instituto Agropolos",
        "category_hint": "servicos", "region": "CE",
    }
    ACADEMIC = {
        "id": "ufjf", "url": "https://www2.ufjf.br/ppgcom/selecao/",
        "kind": "academico", "name": "PPGCOM UFJF",
        "category_hint": "mestrados", "region": "MG",
    }
    CULTURE = {
        "id": "mapa-ce",
        "url": "https://mapacultural.secult.ce.gov.br/projeto/7111/",
        "kind": "cultural", "name": "Mapa Cultural CE",
        "category_hint": "servicos", "region": "CE",
    }

    def test_edital_with_generic_link_keeps_heading(self):
        html = '<h2>EDITAL DE CREDENCIAMENTO Nº 020/2026</h2>' \
               '<p><a href="/editais/edital-de-credenciamento-020-2026/">Confira AQUI</a></p>'
        found = monitor.collect(self.AGRO, html)
        self.assertEqual(len(found), 1)
        self.assertIn("020/2026", found[0]["title"])
        self.assertEqual(found[0]["deadline_at"], None)
        self.assertEqual(found[0]["status"], "Prazo não verificado")

    def test_mestras_program_selection(self):
        html = '<h3><a href="/ppgcom/selecao/mestrado-2027/">Seleção Mestrado 2027</a></h3>'
        found = monitor.collect(self.ACADEMIC, html)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["category"], "mestrados")

    def test_leia_mais_uses_heading(self):
        html = '<h2>PPGCOM abre inscrição de mestrado em Comunicação 2027</h2>' \
               '<a href="/ppgcom/noticias/selecao2027/">Leia Mais »</a>'
        found = monitor.collect(self.ACADEMIC, html)
        self.assertEqual(len(found), 1)
        self.assertIn("Comunicação 2027", found[0]["title"])

    def test_ignores_unrelated_and_external_links(self):
        html = '<a href="https://exemplo.com/edital-2027/">Seleção Mestrado 2027</a>' \
               '<a href="/ppgcom/noticias/">Notícias</a>'
        self.assertEqual(monitor.collect(self.ACADEMIC, html), [])

    def test_cultural_keywords(self):
        html = '<h2>Edital de fotografia e design 2026</h2>' \
               '<a href="/oportunidade/9999/">Saiba mais</a>' \
               '<h2>Evento de culinária regional 2026</h2>' \
               '<a href="/oportunidade/8888/">Saiba mais</a>'
        found = monitor.collect(self.CULTURE, html)
        self.assertEqual(len(found), 1)
        self.assertIn("fotografia", found[0]["title"].lower())

    def test_outdated_edital(self):
        html = '<a href="/ppgcom/selecao/mestrado-2024/">Edital seleção Mestrado 2024</a>'
        self.assertEqual(monitor.collect(self.ACADEMIC, html), [])

    def test_repeated_link_deduplicated(self):
        html = '<a href="/ppgcom/selecao/mestrado-2027/">Seleção Mestrado 2027</a>' * 2
        self.assertEqual(len(monitor.collect(self.ACADEMIC, html)), 1)

    def test_source_title_generic_arrows(self):
        self.assertEqual(
            monitor.source_title("Leia Mais »", "Seleção Mestrado 2027", "https://site.com/a"),
            "Seleção Mestrado 2027"
        )


    def test_pncp_filters_communication_and_keeps_official_link(self):
        from pncp import collect_pncp
        mock_data = {
            "totalPaginas": 1,
            "data": [
                {
                    "objetoCompra": "Serviços especializados de assessoria de comunicação",
                    "orgaoEntidade": {"cnpj": "12345678000199", "razaoSocial": "Órgão estadual"},
                    "anoCompra": 2026, "sequencialCompra": 15,
                    "numeroControlePNCP": "12345678000199-1-15/2026",
                    "dataPublicacaoPncp": "2026-11-16T10:00:00",
                    "dataEncerramentoProposta": "2026-11-24T18:00:00",
                    "valorTotalEstimado": 17000,
                },
                {
                    "objetoCompra": "Compra de papel para impressora e cartuchos",
                    "orgaoEntidade": {"cnpj": "12345678000199", "razaoSocial": "Órgão estadual"},
                    "anoCompra": 2026, "sequencialCompra": 16,
                }
            ]
        }
        found = collect_pncp(
            {"id": "pncp"}, "2026-11-16T00:00:00+00:00",
            monitor.normalize, monitor.COMMS, fetch_json=lambda url: mock_data
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["deadline_at"], "2026-11-24")
        self.assertEqual(
            found[0]["official_url"],
            "https://pncp.gov.br/app/editais/12345678000199/2026/15"
        )


if __name__ == "__main__":
    unittest.main()
