from app.application.services import coletar_ofertas
from app.domain.models import OfferStatus
from app.infrastructure.collectors import FakeColetor


def test_fluxo_completo_coletar_aprovar_publicar_e_historico(
    client, app, sql_repo, seeded
) -> None:
    loja, canal = seeded

    resultado = coletar_ofertas(loja, FakeColetor(), sql_repo)
    assert resultado.inseridas == 3

    fila = client.get("/")
    assert fila.status_code == 200
    assert "Fila de ofertas" in fila.text
    assert "Fone de Ouvido Bluetooth" in fila.text
    assert "Status: pendente de aprovação" in fila.text

    ofertas = sql_repo.listar_ofertas(None, 0, 10)
    alvo = next(item for item in ofertas if "Fone de Ouvido" in item.titulo)

    aprovacao = client.post(f"/ofertas/{alvo.id}/aprovar", follow_redirects=True)
    assert aprovacao.status_code == 200
    assert "Oferta aprovada." in aprovacao.text
    assert "Link válido" in aprovacao.text

    previa = client.get(f"/ofertas/{alvo.id}/previa?canal_id={canal.id}")
    assert previa.status_code == 200
    assert "Prévia da oferta" in previa.text
    assert "afiliado" in previa.text
    assert "Mensagem que será enviada" in previa.text

    publicacao = client.post(
        f"/ofertas/{alvo.id}/publicar",
        data={"canal_id": canal.id},
        follow_redirects=True,
    )
    assert publicacao.status_code == 200
    assert "Histórico de publicações" in publicacao.text
    assert "Fone de Ouvido Bluetooth" in publicacao.text
    assert "enviada com sucesso" in publicacao.text

    historico = client.get(f"/historico?canal_id={canal.id}")
    assert historico.status_code == 200
    assert "Fone de Ouvido Bluetooth" in historico.text
    assert "1 publicação(ões) registrada(s)" in historico.text

    duplicada = client.post(
        f"/ofertas/{alvo.id}/publicar",
        data={"canal_id": canal.id},
        follow_redirects=True,
    )
    assert duplicada.status_code == 200
    assert "já publicada" in duplicada.text
    assert sql_repo.contar_publicacoes(canal.id) == 1


def test_fila_vazia_e_historico_vazio(client) -> None:
    fila = client.get("/")
    assert fila.status_code == 200
    assert "Nenhuma oferta na fila" in fila.text

    historico = client.get("/historico")
    assert historico.status_code == 200
    assert "Nenhuma publicação registrada" in historico.text


def test_paginas_tem_acessibilidade_basica(client, app, sql_repo, seeded) -> None:
    loja, canal = seeded
    coletar_ofertas(loja, FakeColetor(), sql_repo)
    oferta = sql_repo.listar_ofertas(None, 0, 1)[0]

    for url in ("/", f"/ofertas/{oferta.id}/previa", f"/historico?canal_id={canal.id}"):
        resposta = client.get(url)
        assert resposta.status_code == 200
        assert 'lang="pt-BR"' in resposta.text
        assert "Pular para o conteúdo" in resposta.text
        assert "<label" in resposta.text


def test_previa_de_oferta_inexistente_retorna_404(client) -> None:
    assert client.get("/ofertas/inexistente/previa").status_code == 404


def test_aprovar_oferta_inexistente_retorna_404(client) -> None:
    assert client.post("/ofertas/inexistente/aprovar").status_code == 404


def test_publicar_em_canal_inexistente_mostra_erro_tratado(
    client, sql_repo, seeded
) -> None:
    loja, _ = seeded
    coletar_ofertas(loja, FakeColetor(), sql_repo)
    oferta = sql_repo.listar_ofertas([OfferStatus.PENDENTE], 0, 1)[0]

    resposta = client.post(
        f"/ofertas/{oferta.id}/publicar",
        data={"canal_id": "canal-inexistente"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "não encontrado" in resposta.text


def test_aprovar_oferta_ja_aprovada_mostra_erro_tratado(client, sql_repo, seeded) -> None:
    loja, _ = seeded
    coletar_ofertas(loja, FakeColetor(), sql_repo)
    oferta = sql_repo.listar_ofertas([OfferStatus.PENDENTE], 0, 1)[0]

    client.post(f"/ofertas/{oferta.id}/aprovar")
    resposta = client.post(f"/ofertas/{oferta.id}/aprovar", follow_redirects=True)

    assert resposta.status_code == 200
    assert "Somente ofertas pendentes" in resposta.text


def test_publicar_com_falha_de_envio_mostra_erro(client, app, sql_repo, seeded) -> None:
    from app.infrastructure.publishers import FakePublicador

    app.state.publicador = FakePublicador(falhar_sempre=True)
    loja, canal = seeded
    coletar_ofertas(loja, FakeColetor(), sql_repo)
    oferta = sql_repo.listar_ofertas([OfferStatus.PENDENTE], 0, 1)[0]
    client.post(f"/ofertas/{oferta.id}/aprovar")

    resposta = client.post(
        f"/ofertas/{oferta.id}/publicar",
        data={"canal_id": canal.id},
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "Falha simulada" in resposta.text
