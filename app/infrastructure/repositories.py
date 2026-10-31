from __future__ import annotations

from collections.abc import MutableMapping, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.models import (
    Canal,
    LinkValidation,
    Loja,
    Oferta,
    OfferStatus,
    Publicacao,
)
from app.infrastructure.orm import CanalORM, LojaORM, OfertaORM, PublicacaoORM


def _to_loja(orm: LojaORM) -> Loja:
    return Loja(
        id=orm.id,
        nome=orm.nome,
        slug=orm.slug,
        url_base=orm.url_base,
        padrao_link=orm.padrao_link,
        ativo=orm.ativo,
        criado_em=orm.criado_em,
    )


def _to_oferta(orm: OfertaORM) -> Oferta:
    return Oferta(
        id=orm.id,
        loja_id=orm.loja_id,
        id_externo=orm.id_externo,
        id_externo_normalizado=orm.id_externo_normalizado,
        titulo=orm.titulo,
        url_produto=orm.url_produto,
        imagem_url=orm.imagem_url,
        preco_original=orm.preco_original,
        preco_desconto=orm.preco_desconto,
        coletado_em=orm.coletado_em,
        status=orm.status,
        criado_em=orm.criado_em,
        atualizado_em=orm.atualizado_em,
    )


def _to_canal(orm: CanalORM) -> Canal:
    return Canal(
        id=orm.id,
        tipo=orm.tipo,
        nome=orm.nome,
        identificador_externo=orm.identificador_externo,
        ativo=orm.ativo,
        limite_caracteres=orm.limite_caracteres,
        criado_em=orm.criado_em,
    )


def _to_publicacao(orm: PublicacaoORM) -> Publicacao:
    return Publicacao(
        id=orm.id,
        oferta_id=orm.oferta_id,
        canal_id=orm.canal_id,
        link_afiliado=orm.link_afiliado,
        link_validado_em=orm.link_validado_em,
        mensagem_enviada=orm.mensagem_enviada,
        publicada_em=orm.publicada_em,
        status_envio=orm.status_envio,
        erro_detalhe=orm.erro_detalhe,
        criado_em=orm.criado_em,
    )


class RepositorioSQLAlchemy:
    def __init__(
        self,
        session: Session,
        link_cache: MutableMapping[str, LinkValidation] | None = None,
    ) -> None:
        self.session = session
        # Validation happens during preview, before a publication exists. The cache keeps
        # that result available to the publish request in this single-process MVP.
        self.link_cache = link_cache if link_cache is not None else {}

    def criar_loja(self, loja: Loja) -> None:
        self.session.add(
            LojaORM(
                id=loja.id,
                nome=loja.nome,
                slug=loja.slug,
                url_base=loja.url_base,
                padrao_link=loja.padrao_link,
                ativo=loja.ativo,
                criado_em=loja.criado_em,
            )
        )
        self.session.flush()

    def criar_canal(self, canal: Canal) -> None:
        self.session.add(
            CanalORM(
                id=canal.id,
                tipo=canal.tipo,
                nome=canal.nome,
                identificador_externo=canal.identificador_externo,
                ativo=canal.ativo,
                limite_caracteres=canal.limite_caracteres,
                criado_em=canal.criado_em,
            )
        )
        self.session.flush()

    def get_loja(self, loja_id: str) -> Loja | None:
        orm = self.session.get(LojaORM, loja_id)
        return _to_loja(orm) if orm else None

    def get_loja_por_slug(self, slug: str) -> Loja | None:
        orm = self.session.scalar(select(LojaORM).where(LojaORM.slug == slug))
        return _to_loja(orm) if orm else None

    def listar_lojas(self) -> list[Loja]:
        orms = self.session.scalars(select(LojaORM).order_by(LojaORM.nome)).all()
        return [_to_loja(orm) for orm in orms]

    def get_oferta(self, oferta_id: str) -> Oferta | None:
        orm = self.session.get(OfertaORM, oferta_id)
        return _to_oferta(orm) if orm else None

    def get_canal(self, canal_id: str) -> Canal | None:
        orm = self.session.get(CanalORM, canal_id)
        return _to_canal(orm) if orm else None

    def listar_canais(self, apenas_ativos: bool = False) -> list[Canal]:
        stmt = select(CanalORM).order_by(CanalORM.nome)
        if apenas_ativos:
            stmt = stmt.where(CanalORM.ativo.is_(True))
        return [_to_canal(orm) for orm in self.session.scalars(stmt).all()]

    def existe_oferta(self, loja_id: str, id_externo_normalizado: str) -> bool:
        stmt = (
            select(OfertaORM.id)
            .where(OfertaORM.loja_id == loja_id)
            .where(OfertaORM.id_externo_normalizado == id_externo_normalizado)
        )
        return self.session.scalar(stmt) is not None

    def criar_oferta(self, oferta: Oferta) -> None:
        self.session.add(
            OfertaORM(
                id=oferta.id,
                loja_id=oferta.loja_id,
                id_externo=oferta.id_externo,
                id_externo_normalizado=oferta.id_externo_normalizado,
                titulo=oferta.titulo,
                url_produto=oferta.url_produto,
                imagem_url=oferta.imagem_url,
                preco_original=oferta.preco_original,
                preco_desconto=oferta.preco_desconto,
                coletado_em=oferta.coletado_em,
                status=oferta.status,
                criado_em=oferta.criado_em,
                atualizado_em=oferta.atualizado_em,
            )
        )
        self.session.flush()

    def atualizar_oferta(self, oferta: Oferta) -> None:
        orm = self.session.get(OfertaORM, oferta.id)
        if orm is None:
            return
        orm.titulo = oferta.titulo
        orm.url_produto = oferta.url_produto
        orm.imagem_url = oferta.imagem_url
        orm.preco_original = oferta.preco_original
        orm.preco_desconto = oferta.preco_desconto
        orm.status = oferta.status
        orm.atualizado_em = oferta.atualizado_em
        self.session.flush()

    def listar_ofertas(
        self,
        statuses: Sequence[OfferStatus] | None,
        offset: int,
        limit: int,
    ) -> list[Oferta]:
        stmt = select(OfertaORM).order_by(OfertaORM.coletado_em.desc(), OfertaORM.id)
        if statuses is not None:
            stmt = stmt.where(OfertaORM.status.in_(list(statuses)))
        orms = self.session.scalars(stmt.offset(offset).limit(limit)).all()
        return [_to_oferta(orm) for orm in orms]

    def contar_ofertas(self, statuses: Sequence[OfferStatus] | None = None) -> int:
        stmt = select(func.count()).select_from(OfertaORM)
        if statuses is not None:
            stmt = stmt.where(OfertaORM.status.in_(list(statuses)))
        return int(self.session.scalar(stmt) or 0)

    def criar_publicacao(self, publicacao: Publicacao) -> None:
        self.session.add(
            PublicacaoORM(
                id=publicacao.id,
                oferta_id=publicacao.oferta_id,
                canal_id=publicacao.canal_id,
                link_afiliado=publicacao.link_afiliado,
                link_validado_em=publicacao.link_validado_em,
                mensagem_enviada=publicacao.mensagem_enviada,
                publicada_em=publicacao.publicada_em,
                status_envio=publicacao.status_envio,
                erro_detalhe=publicacao.erro_detalhe,
                criado_em=publicacao.criado_em,
            )
        )
        self.session.flush()

    def obter_publicacao(self, oferta_id: str, canal_id: str) -> Publicacao | None:
        stmt = (
            select(PublicacaoORM)
            .where(PublicacaoORM.oferta_id == oferta_id)
            .where(PublicacaoORM.canal_id == canal_id)
        )
        orm = self.session.scalar(stmt)
        return _to_publicacao(orm) if orm else None

    def listar_publicacoes(
        self, canal_id: str | None, offset: int, limit: int
    ) -> list[Publicacao]:
        stmt = select(PublicacaoORM).order_by(PublicacaoORM.criado_em.desc())
        if canal_id is not None:
            stmt = stmt.where(PublicacaoORM.canal_id == canal_id)
        orms = self.session.scalars(stmt.offset(offset).limit(limit)).all()
        return [_to_publicacao(orm) for orm in orms]

    def contar_publicacoes(self, canal_id: str | None) -> int:
        stmt = select(func.count()).select_from(PublicacaoORM)
        if canal_id is not None:
            stmt = stmt.where(PublicacaoORM.canal_id == canal_id)
        return int(self.session.scalar(stmt) or 0)

    def salvar_validacao_link(self, validacao: LinkValidation) -> None:
        self.link_cache[validacao.oferta_id] = validacao

    def obter_validacao_link(self, oferta_id: str) -> LinkValidation | None:
        return self.link_cache.get(oferta_id)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
