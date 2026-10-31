from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum


def utcnow() -> datetime:
    return datetime.now(UTC)


class OfferStatus(StrEnum):
    PENDENTE = "pendente"
    APROVADA = "aprovada"
    PUBLICADA = "publicada"
    DESCARTA = "descartada"


class ChannelType(StrEnum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


class SendStatus(StrEnum):
    OK = "ok"
    FALHA = "falha"


@dataclass
class Loja:
    id: str
    nome: str
    slug: str
    url_base: str
    padrao_link: str
    ativo: bool = True
    criado_em: datetime = field(default_factory=utcnow)


@dataclass
class Oferta:
    id: str
    loja_id: str
    id_externo: str
    id_externo_normalizado: str
    titulo: str
    url_produto: str
    imagem_url: str | None
    preco_original: Decimal
    preco_desconto: Decimal | None
    coletado_em: datetime
    status: OfferStatus
    criado_em: datetime
    atualizado_em: datetime


@dataclass
class Canal:
    id: str
    tipo: ChannelType
    nome: str
    identificador_externo: str
    ativo: bool = True
    limite_caracteres: int | None = None
    criado_em: datetime = field(default_factory=utcnow)


@dataclass
class Publicacao:
    id: str
    oferta_id: str
    canal_id: str
    link_afiliado: str
    link_validado_em: datetime | None
    mensagem_enviada: str | None
    publicada_em: datetime | None
    status_envio: SendStatus
    erro_detalhe: str | None
    criado_em: datetime


@dataclass(frozen=True)
class OfertaColetada:
    """Raw offer as returned by a marketplace collector, before normalization."""

    id_externo: str
    titulo: str
    url_produto: str
    preco_original: Decimal
    preco_desconto: Decimal | None = None
    imagem_url: str | None = None


@dataclass(frozen=True)
class LinkCheck:
    status_code: int
    elapsed_ms: int
    valido: bool
    validado_em: datetime


@dataclass(frozen=True)
class LinkValidation:
    oferta_id: str
    link_afiliado: str
    valido: bool
    status_code: int
    elapsed_ms: int
    validado_em: datetime


@dataclass(frozen=True)
class LinkResultado:
    link_afiliado: str
    valido: bool
    status_code: int
    elapsed_ms: int
    validado_em: datetime


@dataclass(frozen=True)
class EnvioResultado:
    status: SendStatus
    erro: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is SendStatus.OK


@dataclass
class ColetaResultado:
    coletadas: int = 0
    inseridas: int = 0
    duplicadas: int = 0


class DomainError(Exception):
    """Base class for expected domain failures."""


class OfertaNaoEncontradaError(DomainError):
    pass


class LojaNaoEncontradaError(DomainError):
    pass


class CanalNaoEncontradoError(DomainError):
    pass


class TransicaoInvalidaError(DomainError):
    pass


class PublicacaoRecusadaError(DomainError):
    pass


class OfertaJaPublicadaError(DomainError):
    pass
