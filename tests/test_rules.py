from decimal import Decimal

import pytest

from app.domain.models import (
    Canal,
    ChannelType,
    Oferta,
    OfferStatus,
    utcnow,
)
from app.domain.rules import (
    build_offer_key,
    can_publish,
    is_link_valid,
    normalize_external_id,
)


@pytest.mark.parametrize(
    ("raw", "esperado"),
    [
        ("MLB123?ref=abc", "mlb123"),
        ("MLB123#promocao", "mlb123"),
        ("  MLB123/  ", "mlb123"),
        ("MLB 123", "mlb123"),
        ("mlb123", "mlb123"),
        ("", ""),
    ],
)
def test_normalize_external_id(raw: str, esperado: str) -> None:
    assert normalize_external_id(raw) == esperado


def test_build_offer_key_uses_store_and_normalized_id() -> None:
    assert build_offer_key("loja-1", "mlb123") == ("loja-1", "mlb123")


@pytest.mark.parametrize(
    ("status", "elapsed", "esperado"),
    [
        (200, 100, True),
        (204, 100, True),
        (302, 100, True),
        (399, 100, True),
        (199, 100, False),
        (400, 100, False),
        (500, 100, False),
        (200, 5000, True),
        (200, 5001, False),
        (200, -1, False),
    ],
)
def test_is_link_valid_nos_limites(status: int, elapsed: int, esperado: bool) -> None:
    assert is_link_valid(status, elapsed, 5000) is esperado


def _oferta(status: OfferStatus = OfferStatus.APROVADA) -> Oferta:
    agora = utcnow()
    return Oferta(
        id="oferta-1",
        loja_id="loja-1",
        id_externo="MLB1",
        id_externo_normalizado="mlb1",
        titulo="Produto",
        url_produto="https://loja.example/produto",
        imagem_url=None,
        preco_original=Decimal("100.00"),
        preco_desconto=None,
        coletado_em=agora,
        status=status,
        criado_em=agora,
        atualizado_em=agora,
    )


def _canal(ativo: bool = True) -> Canal:
    return Canal(
        id="canal-1",
        tipo=ChannelType.WHATSAPP,
        nome="Grupo",
        identificador_externo="grupo-1",
        ativo=ativo,
    )


def test_can_publish_permite_quando_tudo_esta_ok() -> None:
    permitido, motivo = can_publish(_oferta(), _canal(), False, True)
    assert permitido is True
    assert motivo == "Publicação permitida."


@pytest.mark.parametrize(
    ("oferta", "canal", "ja_publicada", "link_validado", "link_invalido", "trecho"),
    [
        (_oferta(), _canal(), True, True, False, "já publicada"),
        (_oferta(), _canal(), False, False, False, "não foi validado"),
        (_oferta(), _canal(), False, False, True, "inválido"),
        (_oferta(OfferStatus.DESCARTA), _canal(), False, True, False, "descartada"),
        (_oferta(), _canal(ativo=False), False, True, False, "inativo"),
    ],
)
def test_can_publish_recusa_os_casos_invalidos(
    oferta: Oferta,
    canal: Canal,
    ja_publicada: bool,
    link_validado: bool,
    link_invalido: bool,
    trecho: str,
) -> None:
    permitido, motivo = can_publish(
        oferta,
        canal,
        ja_publicada,
        link_validado,
        link_invalido=link_invalido,
    )
    assert permitido is False
    assert trecho in motivo
