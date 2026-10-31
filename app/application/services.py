from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.domain.models import (
    Canal,
    CanalNaoEncontradoError,
    ColetaResultado,
    EnvioResultado,
    LinkCheck,
    LinkResultado,
    LinkValidation,
    Loja,
    LojaNaoEncontradaError,
    Oferta,
    OfertaColetada,
    OfertaJaPublicadaError,
    OfertaNaoEncontradaError,
    OfferStatus,
    Publicacao,
    PublicacaoRecusadaError,
    TransicaoInvalidaError,
    utcnow,
)
from app.domain.rules import build_offer_key, can_publish, normalize_external_id


class Coletor(Protocol):
    def coletar(self, loja: Loja) -> list[OfertaColetada]: ...


class GeradorLink(Protocol):
    def gerar(self, loja: Loja, oferta: Oferta) -> str: ...


class ValidadorLink(Protocol):
    def validar(self, link: str) -> LinkCheck: ...


class Publicador(Protocol):
    def publicar(self, canal: Canal, mensagem: str) -> EnvioResultado: ...


class Repositorio(Protocol):
    def get_loja(self, loja_id: str) -> Loja | None: ...

    def get_oferta(self, oferta_id: str) -> Oferta | None: ...

    def get_canal(self, canal_id: str) -> Canal | None: ...

    def listar_canais(self, apenas_ativos: bool = False) -> list[Canal]: ...

    def existe_oferta(self, loja_id: str, id_externo_normalizado: str) -> bool: ...

    def criar_oferta(self, oferta: Oferta) -> None: ...

    def atualizar_oferta(self, oferta: Oferta) -> None: ...

    def listar_ofertas(
        self,
        statuses: Sequence[OfferStatus] | None,
        offset: int,
        limit: int,
    ) -> list[Oferta]: ...

    def contar_ofertas(self, statuses: Sequence[OfferStatus] | None = None) -> int: ...

    def criar_publicacao(self, publicacao: Publicacao) -> None: ...

    def obter_publicacao(self, oferta_id: str, canal_id: str) -> Publicacao | None: ...

    def listar_publicacoes(
        self, canal_id: str | None, offset: int, limit: int
    ) -> list[Publicacao]: ...

    def contar_publicacoes(self, canal_id: str | None) -> int: ...

    def salvar_validacao_link(self, validacao: LinkValidation) -> None: ...

    def obter_validacao_link(self, oferta_id: str) -> LinkValidation | None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


def coletar_ofertas(loja: Loja, coletor: Coletor, repo: Repositorio) -> ColetaResultado:
    itens = coletor.coletar(loja)
    resultado = ColetaResultado(coletadas=len(itens))
    vistos: set[tuple[str, str]] = set()

    for item in itens:
        normalizado = normalize_external_id(item.id_externo)
        chave = build_offer_key(loja.id, normalizado)
        if not normalizado or chave in vistos or repo.existe_oferta(loja.id, normalizado):
            resultado.duplicadas += 1
            continue

        agora = utcnow()
        oferta = Oferta(
            id=str(uuid4()),
            loja_id=loja.id,
            id_externo=item.id_externo,
            id_externo_normalizado=normalizado,
            titulo=item.titulo,
            url_produto=item.url_produto,
            imagem_url=item.imagem_url,
            preco_original=item.preco_original,
            preco_desconto=item.preco_desconto,
            coletado_em=agora,
            status=OfferStatus.PENDENTE,
            criado_em=agora,
            atualizado_em=agora,
        )
        try:
            repo.criar_oferta(oferta)
            repo.commit()
        except IntegrityError:
            # Another scheduler run inserted the same natural key first; that is not an error.
            repo.rollback()
            resultado.duplicadas += 1
            continue

        vistos.add(chave)
        resultado.inseridas += 1

    return resultado


def aprovar_oferta(oferta_id: str, repo: Repositorio) -> Oferta:
    oferta = repo.get_oferta(oferta_id)
    if oferta is None:
        raise OfertaNaoEncontradaError(f"Oferta {oferta_id} não encontrada.")
    if oferta.status is not OfferStatus.PENDENTE:
        raise TransicaoInvalidaError("Somente ofertas pendentes podem ser aprovadas.")

    oferta.status = OfferStatus.APROVADA
    oferta.atualizado_em = utcnow()
    repo.atualizar_oferta(oferta)
    repo.commit()
    return oferta


def gerar_e_validar_link(
    oferta: Oferta,
    gerador: GeradorLink,
    validador: ValidadorLink,
    repo: Repositorio,
) -> LinkResultado:
    loja = repo.get_loja(oferta.loja_id)
    if loja is None:
        raise LojaNaoEncontradaError(f"Loja {oferta.loja_id} não encontrada.")

    link = gerador.gerar(loja, oferta)
    check = validador.validar(link)
    validacao = LinkValidation(
        oferta_id=oferta.id,
        link_afiliado=link,
        valido=check.valido,
        status_code=check.status_code,
        elapsed_ms=check.elapsed_ms,
        validado_em=check.validado_em,
    )
    repo.salvar_validacao_link(validacao)
    repo.commit()

    return LinkResultado(
        link_afiliado=link,
        valido=check.valido,
        status_code=check.status_code,
        elapsed_ms=check.elapsed_ms,
        validado_em=check.validado_em,
    )


def publicar(
    oferta_id: str,
    canal_id: str,
    publicador: Publicador,
    repo: Repositorio,
) -> Publicacao:
    oferta = repo.get_oferta(oferta_id)
    if oferta is None:
        raise OfertaNaoEncontradaError(f"Oferta {oferta_id} não encontrada.")
    canal = repo.get_canal(canal_id)
    if canal is None:
        raise CanalNaoEncontradoError(f"Canal {canal_id} não encontrado.")

    ja_publicada = repo.obter_publicacao(oferta_id, canal_id) is not None
    validacao = repo.obter_validacao_link(oferta_id)
    link_validado = validacao is not None and validacao.valido
    link_invalido = validacao is not None and not validacao.valido

    permitido, motivo = can_publish(
        oferta,
        canal,
        ja_publicada,
        link_validado,
        link_invalido=link_invalido,
    )
    if not permitido:
        if ja_publicada:
            raise OfertaJaPublicadaError(motivo)
        raise PublicacaoRecusadaError(motivo)

    assert validacao is not None  # garantido por can_publish
    mensagem = montar_mensagem(oferta, validacao.link_afiliado, canal.limite_caracteres)
    envio = publicador.publicar(canal, mensagem)
    agora = utcnow()
    publicacao = Publicacao(
        id=str(uuid4()),
        oferta_id=oferta_id,
        canal_id=canal_id,
        link_afiliado=validacao.link_afiliado,
        link_validado_em=validacao.validado_em,
        mensagem_enviada=mensagem,
        publicada_em=agora if envio.ok else None,
        status_envio=envio.status,
        erro_detalhe=envio.erro,
        criado_em=agora,
    )

    try:
        repo.criar_publicacao(publicacao)
        if envio.ok:
            oferta.status = OfferStatus.PUBLICADA
            oferta.atualizado_em = agora
            repo.atualizar_oferta(oferta)
        repo.commit()
    except IntegrityError as exc:
        repo.rollback()
        raise OfertaJaPublicadaError("Oferta já publicada neste canal.") from exc

    return publicacao


def consultar_historico(
    canal_id: str | None,
    repo: Repositorio,
    page: int,
    per_page: int = 20,
) -> list[Publicacao]:
    page = max(page, 1)
    return repo.listar_publicacoes(canal_id, (page - 1) * per_page, per_page)


def montar_mensagem(oferta: Oferta, link_afiliado: str, limite: int | None = None) -> str:
    preco_original = _formatar_preco(oferta.preco_original)
    if oferta.preco_desconto is not None:
        preco = (
            f"De {preco_original} por {_formatar_preco(oferta.preco_desconto)}"
        )
    else:
        preco = f"Por {preco_original}"

    titulo = oferta.titulo.strip()
    mensagem = f"🔥 {titulo}\n{preco}\n{link_afiliado}"
    if limite is None or len(mensagem) <= limite:
        return mensagem

    # Preserve the link intact: only the title is shortened when the channel has a limit.
    excedente = len(mensagem) - limite
    titulo_max = max(1, len(titulo) - excedente - 1)
    titulo_curto = titulo[:titulo_max].rstrip() + "…"
    return f"🔥 {titulo_curto}\n{preco}\n{link_afiliado}"


def _formatar_preco(valor: Decimal) -> str:
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")
