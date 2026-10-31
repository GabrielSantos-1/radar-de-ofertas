from __future__ import annotations

from decimal import Decimal

from app.domain.models import Loja, OfertaColetada


class FakeColetor:
    """Deterministic collector used by the MVP and by tests.

    The interface is the same one a real marketplace adapter will implement: given a
    store, return raw offers. Swapping it does not touch the application layer.
    """

    def __init__(self, itens: list[OfertaColetada] | None = None) -> None:
        self._itens = itens

    def coletar(self, loja: Loja) -> list[OfertaColetada]:
        if self._itens is not None:
            return list(self._itens)

        base = loja.url_base.rstrip("/")
        prefixo = loja.slug.upper()
        return [
            OfertaColetada(
                id_externo=f"{prefixo}-1001?ref=radar",
                titulo="Fone de Ouvido Bluetooth com Cancelamento de Ruído",
                url_produto=f"{base}/produto/fone-bluetooth",
                preco_original=Decimal("399.90"),
                preco_desconto=Decimal("249.90"),
                imagem_url=f"{base}/imagens/fone.jpg",
            ),
            OfertaColetada(
                id_externo=f"{prefixo}-1002",
                titulo="Air Fryer 5 Litros com Timer Digital",
                url_produto=f"{base}/produto/air-fryer",
                preco_original=Decimal("549.00"),
                preco_desconto=Decimal("389.90"),
                imagem_url=f"{base}/imagens/air-fryer.jpg",
            ),
            OfertaColetada(
                id_externo=f"{prefixo}-1003#promocao",
                titulo="Kit Três Panelas Antiaderentes",
                url_produto=f"{base}/produto/kit-panelas",
                preco_original=Decimal("289.90"),
                preco_desconto=None,
                imagem_url=None,
            ),
        ]
