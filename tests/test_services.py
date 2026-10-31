from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.application.services import (
    aprovar_oferta,
    coletar_ofertas,
    consultar_historico,
    gerar_e_validar_link,
    montar_mensagem,
    publicar,
)
from app.domain.models import (
    CanalNaoEncontradoError,
    OfertaJaPublicadaError,
    OfertaNaoEncontradaError,
    OfferStatus,
    PublicacaoRecusadaError,
    SendStatus,
    TransicaoInvalidaError,
)
from app.infrastructure.affiliate import GeradorLinkAfiliado
from app.infrastructure.collectors import FakeColetor
from app.infrastructure.publishers import FakePublicador
from tests.conftest import FakeRepositorio, FakeValidador


def test_coleta_insere_ineditas_e_ignora_duplicatas(loja, coletor) -> None:
    repositorio = FakeRepositorio()
    repositorio.lojas[loja.id] = loja

    resultado = coletar_ofertas(loja, FakeColetor(coletor), repositorio)

    assert resultado.coletadas == 3
    assert resultado.inseridas == 2
    assert resultado.duplicadas == 1
    assert repositorio.contar_ofertas() == 2

    segunda = coletar_ofertas(loja, FakeColetor(coletor), repositorio)
    assert segunda.inseridas == 0
    assert segunda.duplicadas == 3
    assert repositorio.contar_ofertas() == 2


def test_coleta_ignora_conflito_de_unicidade(loja) -> None:
    class RepositorioCorrida(FakeRepositorio):
        def criar_oferta(self, oferta) -> None:
            raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    repositorio = RepositorioCorrida()
    repositorio.lojas[loja.id] = loja
    item = FakeColetor().coletar(loja)[0]

    resultado = coletar_ofertas(loja, FakeColetor([item]), repositorio)

    assert resultado.inseridas == 0
    assert resultado.duplicadas == 1
    assert repositorio.rollbacks == 1


def test_aprovar_oferta_inexistente_falha(repo) -> None:
    with pytest.raises(OfertaNaoEncontradaError):
        aprovar_oferta("inexistente", repo)


def test_aprovar_oferta_fora_de_pendente_falha(repo, oferta_pendente) -> None:
    oferta_pendente.status = OfferStatus.APROVADA
    with pytest.raises(TransicaoInvalidaError):
        aprovar_oferta(oferta_pendente.id, repo)


def test_aprovar_oferta_pendente(repo, oferta_pendente) -> None:
    aprovada = aprovar_oferta(oferta_pendente.id, repo)
    assert aprovada.status is OfferStatus.APROVADA
    assert repo.commits == 1


def test_gerar_e_validar_link_registra_validacao(repo, oferta_pendente) -> None:
    resultado = gerar_e_validar_link(
        oferta_pendente,
        GeradorLinkAfiliado(),
        FakeValidador(),
        repo,
    )

    assert resultado.valido is True
    assert "afiliado/mlb123" in resultado.link_afiliado
    assert repo.obter_validacao_link(oferta_pendente.id) is not None


def test_publicar_sem_link_validado_recusa(repo, oferta_pendente, canal) -> None:
    oferta_pendente.status = OfferStatus.APROVADA

    with pytest.raises(PublicacaoRecusadaError, match="validado"):
        publicar(oferta_pendente.id, canal.id, FakePublicador(), repo)


def test_publicar_com_link_invalido_recusa(repo, oferta_pendente, canal) -> None:
    oferta_pendente.status = OfferStatus.APROVADA
    gerar_e_validar_link(oferta_pendente, GeradorLinkAfiliado(), FakeValidador(False), repo)

    with pytest.raises(PublicacaoRecusadaError, match="inválido"):
        publicar(oferta_pendente.id, canal.id, FakePublicador(), repo)


def test_publicar_canal_inexistente_falha(repo, oferta_pendente) -> None:
    with pytest.raises(CanalNaoEncontradoError):
        publicar(oferta_pendente.id, "inexistente", FakePublicador(), repo)


def test_publicar_duas_vezes_no_mesmo_canal_levanta_erro(
    repo, oferta_pendente, canal
) -> None:
    oferta_pendente.status = OfferStatus.APROVADA
    gerar_e_validar_link(oferta_pendente, GeradorLinkAfiliado(), FakeValidador(), repo)
    publicador = FakePublicador()

    publicar(oferta_pendente.id, canal.id, publicador, repo)

    with pytest.raises(OfertaJaPublicadaError):
        publicar(oferta_pendente.id, canal.id, publicador, repo)


def test_publicar_em_canais_diferentes_funciona(
    repo, oferta_pendente, canal, canal_telegram
) -> None:
    oferta_pendente.status = OfferStatus.APROVADA
    gerar_e_validar_link(oferta_pendente, GeradorLinkAfiliado(), FakeValidador(), repo)
    publicador = FakePublicador()

    primeira = publicar(oferta_pendente.id, canal.id, publicador, repo)
    segunda = publicar(oferta_pendente.id, canal_telegram.id, publicador, repo)

    assert primeira.canal_id != segunda.canal_id
    assert primeira.status_envio is SendStatus.OK
    assert segunda.status_envio is SendStatus.OK
    assert len(publicador.enviados) == 2
    assert oferta_pendente.status is OfferStatus.PUBLICADA


def test_publicar_converte_conflito_de_unicidade(
    repo, oferta_pendente, canal
) -> None:
    class RepositorioConflito(FakeRepositorio):
        def criar_publicacao(self, publicacao) -> None:
            raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    oferta_pendente.status = OfferStatus.APROVADA
    gerar_e_validar_link(oferta_pendente, GeradorLinkAfiliado(), FakeValidador(), repo)
    conflito = RepositorioConflito()
    conflito.lojas.update(repo.lojas)
    conflito.ofertas.update(repo.ofertas)
    conflito.canais.update(repo.canais)
    conflito.validacoes.update(repo.validacoes)

    with pytest.raises(OfertaJaPublicadaError):
        publicar(oferta_pendente.id, canal.id, FakePublicador(), conflito)

    assert conflito.rollbacks == 1


def test_publicacao_com_falha_de_envio_fica_registrada(
    repo, oferta_pendente, canal
) -> None:
    oferta_pendente.status = OfferStatus.APROVADA
    gerar_e_validar_link(oferta_pendente, GeradorLinkAfiliado(), FakeValidador(), repo)

    publicacao = publicar(oferta_pendente.id, canal.id, FakePublicador(falhar_sempre=True), repo)

    assert publicacao.status_envio is SendStatus.FALHA
    assert publicacao.publicada_em is None
    assert publicacao.erro_detalhe
    assert oferta_pendente.status is OfferStatus.APROVADA


def test_consultar_historico_pagina(repo, oferta_pendente, canal, canal_telegram) -> None:
    oferta_pendente.status = OfferStatus.APROVADA
    gerar_e_validar_link(oferta_pendente, GeradorLinkAfiliado(), FakeValidador(), repo)
    publicador = FakePublicador()
    publicar(oferta_pendente.id, canal.id, publicador, repo)
    publicar(oferta_pendente.id, canal_telegram.id, publicador, repo)

    primeira_pagina = consultar_historico(canal.id, repo, 1, per_page=1)
    segunda_pagina = consultar_historico(canal.id, repo, 2, per_page=1)

    assert len(primeira_pagina) == 1
    assert primeira_pagina[0].canal_id == canal.id
    assert segunda_pagina == []


def test_montar_mensagem_inclui_precos_e_link(oferta_pendente) -> None:
    mensagem = montar_mensagem(oferta_pendente, "https://link.example")
    assert "Fone de Ouvido Bluetooth" in mensagem
    assert "R$ 399,90" in mensagem
    assert "R$ 249,90" in mensagem
    assert "https://link.example" in mensagem


def test_montar_mensagem_sem_desconto(oferta_pendente) -> None:
    oferta_pendente.preco_desconto = None
    mensagem = montar_mensagem(oferta_pendente, "https://link.example")
    assert "Por R$ 399,90" in mensagem


def test_montar_mensagem_respeita_limite_do_canal(oferta_pendente) -> None:
    link = "https://link.example/afiliado/mlb123"
    mensagem = montar_mensagem(oferta_pendente, link, limite=70)

    assert len(mensagem) <= 70
    assert link in mensagem
    assert mensagem.startswith("🔥 ")
    assert "…" in mensagem


def test_montar_mensagem_com_preco_decimal(loja, oferta_pendente) -> None:
    oferta_pendente.preco_original = Decimal("1000.00")
    mensagem = montar_mensagem(oferta_pendente, "https://link.example")
    assert "R$ 1.000,00" in mensagem
