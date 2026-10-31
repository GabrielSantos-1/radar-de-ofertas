from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models import ChannelType, OfferStatus, SendStatus
from app.infrastructure.db import Base


def _enum(enum_cls: type, name: str) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        values_callable=lambda cls: [item.value for item in cls],
        validate_strings=True,
    )


class LojaORM(Base):
    __tablename__ = "loja"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    url_base: Mapped[str] = mapped_column(String(500), nullable=False)
    padrao_link: Mapped[str] = mapped_column(String(500), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OfertaORM(Base):
    __tablename__ = "oferta"
    __table_args__ = (
        UniqueConstraint(
            "loja_id",
            "id_externo_normalizado",
            name="uq_oferta_loja_id_externo",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    loja_id: Mapped[str] = mapped_column(ForeignKey("loja.id"), nullable=False)
    id_externo: Mapped[str] = mapped_column(String(200), nullable=False)
    id_externo_normalizado: Mapped[str] = mapped_column(String(200), nullable=False)
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    url_produto: Mapped[str] = mapped_column(String(1000), nullable=False)
    imagem_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    preco_original: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    preco_desconto: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    coletado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[OfferStatus] = mapped_column(
        _enum(OfferStatus, "offer_status"), nullable=False
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CanalORM(Base):
    __tablename__ = "canal"
    __table_args__ = (
        UniqueConstraint("tipo", "identificador_externo", name="uq_canal_tipo_identificador"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tipo: Mapped[ChannelType] = mapped_column(
        _enum(ChannelType, "channel_type"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    identificador_externo: Mapped[str] = mapped_column(String(200), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    limite_caracteres: Mapped[int | None] = mapped_column(nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PublicacaoORM(Base):
    __tablename__ = "publicacao"
    __table_args__ = (
        UniqueConstraint("oferta_id", "canal_id", name="uq_publicacao_oferta_canal"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    oferta_id: Mapped[str] = mapped_column(ForeignKey("oferta.id"), nullable=False)
    canal_id: Mapped[str] = mapped_column(ForeignKey("canal.id"), nullable=False)
    link_afiliado: Mapped[str] = mapped_column(String(1000), nullable=False)
    link_validado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mensagem_enviada: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    publicada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status_envio: Mapped[SendStatus] = mapped_column(
        _enum(SendStatus, "send_status"), nullable=False
    )
    erro_detalhe: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
