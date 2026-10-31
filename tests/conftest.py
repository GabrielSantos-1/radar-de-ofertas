from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.domain.models import (
    Canal,
    ChannelType,
    LinkCheck,
    LinkValidation,
    Loja,
    Oferta,
    OfertaColetada,
    OfferStatus,
    Publicacao,
    utcnow,
)
from app.infrastructure.repositories import RepositorioSQLAlchemy
from app.main import create_app

AGORA = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


class FakeValidador:
    def __init__(self, valido: bool = True) -> None:
        self.valido = valido

    def validar(self, link: str) -> LinkCheck:
        return LinkCheck(
            status_code=200 if self.valido else 404,
            elapsed_ms=40,
            valido=self.valido,
            validado_em=utcnow(),
        )


class FakeRepositorio:
    def __init__(self) -> None:
        self.lojas: dict[str, Loja] = {}
        self.ofertas: dict[str, Oferta] = {}
        self.canais: dict[str, Canal] = {}
        self.publicacoes: dict[tuple[str, str], Publicacao] = {}
        self.validacoes: dict[str, LinkValidation] = {}
        self.commits = 0
        self.rollbacks = 0

    def get_loja(self, loja_id: str) -> Loja | None:
        return self.lojas.get(loja_id)

    def get_oferta(self, oferta_id: str) -> Oferta | None:
        return self.ofertas.get(oferta_id)

    def get_canal(self, canal_id: str) -> Canal | None:
        return self.canais.get(canal_id)

    def listar_canais(self, apenas_ativos: bool = False) -> list[Canal]:
        canais = list(self.canais.values())
        if apenas_ativos:
            canais = [canal for canal in canais if canal.ativo]
        return canais

    def existe_oferta(self, loja_id: str, id_externo_normalizado: str) -> bool:
        return any(
            oferta.loja_id == loja_id
            and oferta.id_externo_normalizado == id_externo_normalizado
            for oferta in self.ofertas.values()
        )

    def criar_oferta(self, oferta: Oferta) -> None:
        self.ofertas[oferta.id] = oferta

    def atualizar_oferta(self, oferta: Oferta) -> None:
        self.ofertas[oferta.id] = oferta

    def listar_ofertas(
        self,
        statuses: Sequence[OfferStatus] | None,
        offset: int,
        limit: int,
    ) -> list[Oferta]:
        ofertas = sorted(
            self.ofertas.values(),
            key=lambda item: item.coletado_em,
            reverse=True,
        )
        if statuses is not None:
            ofertas = [item for item in ofertas if item.status in statuses]
        return ofertas[offset : offset + limit]

    def contar_ofertas(self, statuses: Sequence[OfferStatus] | None = None) -> int:
        if statuses is None:
            return len(self.ofertas)
        return sum(1 for item in self.ofertas.values() if item.status in statuses)

    def criar_publicacao(self, publicacao: Publicacao) -> None:
        chave = (publicacao.oferta_id, publicacao.canal_id)
        if chave in self.publicacoes:
            raise IntegrityError("INSERT", {}, Exception("duplicate key"))
        self.publicacoes[chave] = publicacao

    def obter_publicacao(self, oferta_id: str, canal_id: str) -> Publicacao | None:
        return self.publicacoes.get((oferta_id, canal_id))

    def listar_publicacoes(
        self, canal_id: str | None, offset: int, limit: int
    ) -> list[Publicacao]:
        publicacoes = sorted(
            self.publicacoes.values(),
            key=lambda item: item.criado_em,
            reverse=True,
        )
        if canal_id is not None:
            publicacoes = [item for item in publicacoes if item.canal_id == canal_id]
        return publicacoes[offset : offset + limit]

    def contar_publicacoes(self, canal_id: str | None) -> int:
        if canal_id is None:
            return len(self.publicacoes)
        return sum(1 for item in self.publicacoes.values() if item.canal_id == canal_id)

    def salvar_validacao_link(self, validacao: LinkValidation) -> None:
        self.validacoes[validacao.oferta_id] = validacao

    def obter_validacao_link(self, oferta_id: str) -> LinkValidation | None:
        return self.validacoes.get(oferta_id)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


@pytest.fixture
def loja() -> Loja:
    return Loja(
        id=str(uuid4()),
        nome="Loja Teste",
        slug="loja-teste",
        url_base="https://loja-teste.example",
        padrao_link="https://loja-teste.example/afiliado/{id}?url={url}",
        criado_em=AGORA,
    )


@pytest.fixture
def canal() -> Canal:
    return Canal(
        id=str(uuid4()),
        tipo=ChannelType.WHATSAPP,
        nome="Grupo WhatsApp",
        identificador_externo="grupo-123",
        limite_caracteres=2000,
        criado_em=AGORA,
    )


@pytest.fixture
def canal_telegram() -> Canal:
    return Canal(
        id=str(uuid4()),
        tipo=ChannelType.TELEGRAM,
        nome="Canal Telegram",
        identificador_externo="@radar",
        limite_caracteres=1000,
        criado_em=AGORA,
    )


@pytest.fixture
def oferta_pendente(loja: Loja) -> Oferta:
    return Oferta(
        id=str(uuid4()),
        loja_id=loja.id,
        id_externo="MLB123?ref=abc",
        id_externo_normalizado="mlb123",
        titulo="Fone de Ouvido Bluetooth",
        url_produto="https://loja-teste.example/produto/fone",
        imagem_url=None,
        preco_original=Decimal("399.90"),
        preco_desconto=Decimal("249.90"),
        coletado_em=AGORA,
        status=OfferStatus.PENDENTE,
        criado_em=AGORA,
        atualizado_em=AGORA,
    )


@pytest.fixture
def repo(
    loja: Loja,
    canal: Canal,
    canal_telegram: Canal,
    oferta_pendente: Oferta,
) -> FakeRepositorio:
    repositorio = FakeRepositorio()
    repositorio.lojas[loja.id] = loja
    repositorio.canais[canal.id] = canal
    repositorio.canais[canal_telegram.id] = canal_telegram
    repositorio.ofertas[oferta_pendente.id] = oferta_pendente
    return repositorio


@pytest.fixture
def coletor() -> list[OfertaColetada]:
    return [
        OfertaColetada(
            id_externo="MLB123?ref=abc",
            titulo="Fone de Ouvido Bluetooth",
            url_produto="https://loja-teste.example/produto/fone",
            preco_original=Decimal("399.90"),
            preco_desconto=Decimal("249.90"),
        ),
        OfertaColetada(
            id_externo="MLB123#fragmento",
            titulo="Fone de Ouvido Bluetooth",
            url_produto="https://loja-teste.example/produto/fone",
            preco_original=Decimal("399.90"),
            preco_desconto=Decimal("249.90"),
        ),
        OfertaColetada(
            id_externo="MLB456",
            titulo="Air Fryer 5 Litros",
            url_produto="https://loja-teste.example/produto/air-fryer",
            preco_original=Decimal("549.00"),
            preco_desconto=Decimal("389.90"),
        ),
    ]


@pytest.fixture
def app():
    settings = Settings(database_url="sqlite://", page_size=20, link_timeout_ms=1000)
    return create_app(settings, validator=FakeValidador())


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seeded(app) -> tuple[Loja, Canal]:
    session = app.state.session_factory()
    repositorio = RepositorioSQLAlchemy(session, app.state.link_cache)
    loja = Loja(
        id=str(uuid4()),
        nome="Mercado Livre",
        slug="mercado-livre",
        url_base="https://mercadolivre.example",
        padrao_link="https://mercadolivre.example/afiliado/{id}?url={url}",
        criado_em=AGORA,
    )
    canal = Canal(
        id=str(uuid4()),
        tipo=ChannelType.WHATSAPP,
        nome="Grupo de Ofertas",
        identificador_externo="grupo-123",
        limite_caracteres=2000,
        criado_em=AGORA,
    )
    repositorio.criar_loja(loja)
    repositorio.criar_canal(canal)
    repositorio.commit()
    session.close()
    return loja, canal


@pytest.fixture
def sql_repo(app) -> RepositorioSQLAlchemy:
    session = app.state.session_factory()
    repositorio = RepositorioSQLAlchemy(session, app.state.link_cache)
    yield repositorio
    session.close()
