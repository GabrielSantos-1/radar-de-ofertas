from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

from app.application.services import Coletor, GeradorLink, Publicador, ValidadorLink
from app.config import Settings, get_settings
from app.infrastructure.affiliate import GeradorLinkAfiliado
from app.infrastructure.collectors import FakeColetor
from app.infrastructure.db import Base, build_engine, build_session_factory
from app.infrastructure.link_validator import HttpxLinkValidator
from app.infrastructure.publishers import FakePublicador
from app.web.routes import router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


def create_app(
    settings: Settings | None = None,
    *,
    validator: ValidadorLink | None = None,
    publicador: Publicador | None = None,
    gerador: GeradorLink | None = None,
    coletor: Coletor | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)
    Base.metadata.create_all(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(title="Radar de Ofertas", lifespan=lifespan)
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.link_cache = {}
    app.state.validator = validator or HttpxLinkValidator(settings.link_timeout_ms)
    app.state.publicador = publicador or FakePublicador()
    app.state.gerador = gerador or GeradorLinkAfiliado()
    app.state.coletor = coletor or FakeColetor()

    app.include_router(router)

    @app.get("/health", tags=["infra"])
    def health() -> dict[str, str]:
        """Sonda de saúde para monitoramento e para o futuro deploy.

        Deliberadamente não toca no banco: se este processo responde, está de pé.
        Uma checagem de dependência aqui faria o monitoramento reiniciar a aplicação
        por causa de uma indisponibilidade passageira do banco, que é justamente o
        que não se quer.
        """
        return {"status": "ok", "servico": "radar-de-ofertas"}

    return app


app = create_app()
