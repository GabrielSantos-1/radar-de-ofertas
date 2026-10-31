"""Populate a fresh database with fictional stores, channels and offers."""

from __future__ import annotations

from uuid import uuid4

from app.application.services import coletar_ofertas
from app.config import get_settings
from app.domain.models import Canal, ChannelType, Loja
from app.infrastructure.collectors import FakeColetor
from app.infrastructure.db import Base, build_engine, build_session_factory
from app.infrastructure.repositories import RepositorioSQLAlchemy

LOJAS = [
    {
        "nome": "Mercado Livre",
        "slug": "mercado-livre",
        "url_base": "https://mercadolivre.example",
        "padrao_link": "https://mercadolivre.example/afiliado/{id}?url={url}",
    },
    {
        "nome": "Amazon",
        "slug": "amazon",
        "url_base": "https://amazon.example",
        "padrao_link": "https://amazon.example/afiliado/{id}?url={url}",
    },
]

CANAIS = [
    {
        "tipo": ChannelType.WHATSAPP,
        "nome": "Grupo Ofertas do Dia",
        "identificador_externo": "grupo-ofertas-do-dia",
        "limite_caracteres": 2000,
    },
    {
        "tipo": ChannelType.TELEGRAM,
        "nome": "Canal Radar de Ofertas",
        "identificador_externo": "@radar_de_ofertas",
        "limite_caracteres": 1024,
    },
]


def main() -> None:
    settings = get_settings()
    engine = build_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session = build_session_factory(engine)()
    repositorio = RepositorioSQLAlchemy(session)

    lojas: list[Loja] = []
    for dados in LOJAS:
        loja = repositorio.get_loja_por_slug(dados["slug"])
        if loja is None:
            loja = Loja(id=str(uuid4()), **dados)
            repositorio.criar_loja(loja)
            repositorio.commit()
            print(f"Loja criada: {loja.nome}")
        lojas.append(loja)

    existentes = {canal.nome for canal in repositorio.listar_canais()}
    for dados in CANAIS:
        if dados["nome"] not in existentes:
            canal = Canal(id=str(uuid4()), **dados)
            repositorio.criar_canal(canal)
            repositorio.commit()
            print(f"Canal criado: {canal.nome}")

    coletor = FakeColetor()
    for loja in lojas:
        resultado = coletar_ofertas(loja, coletor, repositorio)
        print(
            f"{loja.nome}: {resultado.coletadas} coletadas, "
            f"{resultado.inseridas} inseridas, {resultado.duplicadas} duplicadas"
        )

    session.close()
    engine.dispose()


if __name__ == "__main__":
    main()
