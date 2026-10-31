from app.domain.models import Loja, Oferta


class GeradorLinkAfiliado:
    """Deterministic affiliate link generator for the MVP.

    Each store carries its own link pattern, so a real provider can replace this class
    without changing use cases.
    """

    def gerar(self, loja: Loja, oferta: Oferta) -> str:
        return loja.padrao_link.format(
            url=oferta.url_produto,
            id=oferta.id_externo_normalizado,
            loja=loja.slug,
        )
