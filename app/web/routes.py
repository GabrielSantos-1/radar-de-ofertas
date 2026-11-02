from __future__ import annotations

from math import ceil
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.application.services import (
    aprovar_oferta,
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
from app.infrastructure.repositories import RepositorioSQLAlchemy

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter()


def _moeda(valor: object) -> str:
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


templates.env.filters["moeda"] = _moeda


def get_repo(request: Request):
    session = request.app.state.session_factory()
    try:
        yield RepositorioSQLAlchemy(session, request.app.state.link_cache)
    finally:
        session.close()


RepositorioDep = Annotated[RepositorioSQLAlchemy, Depends(get_repo)]


def _previa_url(oferta_id: str, erro: str | None = None, sucesso: str | None = None) -> str:
    url = f"/ofertas/{oferta_id}/previa"
    params = []
    if erro:
        params.append(f"erro={quote(erro)}")
    if sucesso:
        params.append(f"sucesso={quote(sucesso)}")
    return f"{url}?{'&'.join(params)}" if params else url


def _paginacao(page: int, total: int, per_page: int) -> tuple[int, int]:
    total_pages = max(1, ceil(total / per_page))
    return min(max(page, 1), total_pages), total_pages


@router.get("/", response_class=HTMLResponse)
def fila(
    request: Request,
    repo: RepositorioDep,
    page: int = 1,
    sucesso: str = "",
    erro: str = "",
) -> HTMLResponse:
    settings = request.app.state.settings
    statuses = [OfferStatus.PENDENTE, OfferStatus.APROVADA]
    total = repo.contar_ofertas(statuses)
    page, total_pages = _paginacao(page, total, settings.page_size)
    ofertas = repo.listar_ofertas(
        statuses,
        (page - 1) * settings.page_size,
        settings.page_size,
    )
    lojas = {loja.id: loja for loja in repo.listar_lojas()}
    itens = [{"oferta": oferta, "loja": lojas.get(oferta.loja_id)} for oferta in ofertas]

    return templates.TemplateResponse(
        request=request,
        name="fila.html",
        context={
            "itens": itens,
            "canais": repo.listar_canais(),
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "sucesso": sucesso,
            "erro": erro,
        },
    )


@router.get("/ofertas/{oferta_id}/previa", response_class=HTMLResponse)
def previa(
    request: Request,
    oferta_id: str,
    repo: RepositorioDep,
    canal_id: str | None = None,
    erro: str | None = None,
    sucesso: str | None = None,
) -> HTMLResponse:
    oferta = repo.get_oferta(oferta_id)
    if oferta is None:
        raise HTTPException(status_code=404, detail="Oferta não encontrada.")

    loja = repo.get_loja(oferta.loja_id)
    canais = repo.listar_canais(apenas_ativos=True)
    canal = next((item for item in canais if item.id == canal_id), None)
    if canal is None and canais:
        canal = canais[0]

    link = gerar_e_validar_link(
        oferta,
        request.app.state.gerador,
        request.app.state.validator,
        repo,
    )
    mensagem = montar_mensagem(
        oferta,
        link.link_afiliado,
        canal.limite_caracteres if canal else None,
    )
    ja_publicada = (
        repo.obter_publicacao(oferta.id, canal.id) is not None if canal is not None else False
    )

    return templates.TemplateResponse(
        request=request,
        name="previa.html",
        context={
            "oferta": oferta,
            "loja": loja,
            "canais": canais,
            "canal_selecionado": canal,
            "link": link,
            "mensagem": mensagem,
            "ja_publicada": ja_publicada,
            "erro": erro,
            "sucesso": sucesso,
        },
    )


@router.post("/ofertas/{oferta_id}/aprovar")
def aprovar(request: Request, oferta_id: str, repo: RepositorioDep) -> RedirectResponse:
    try:
        aprovar_oferta(oferta_id, repo)
    except OfertaNaoEncontradaError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TransicaoInvalidaError as exc:
        return RedirectResponse(
            _previa_url(oferta_id, erro=str(exc)),
            status_code=303,
        )
    return RedirectResponse(
        _previa_url(oferta_id, sucesso="Oferta aprovada."),
        status_code=303,
    )


@router.post("/ofertas/{oferta_id}/publicar")
def publicar_oferta(
    request: Request,
    oferta_id: str,
    repo: RepositorioDep,
    canal_id: Annotated[str, Form()],
) -> RedirectResponse:
    try:
        publicacao = publicar(
            oferta_id,
            canal_id,
            request.app.state.publicador,
            repo,
        )
    except (OfertaJaPublicadaError, PublicacaoRecusadaError, CanalNaoEncontradoError) as exc:
        return RedirectResponse(
            _previa_url(oferta_id, erro=str(exc)),
            status_code=303,
        )
    except OfertaNaoEncontradaError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if publicacao.status_envio is SendStatus.FALHA:
        detalhe = publicacao.erro_detalhe or "Falha desconhecida no envio."
        return RedirectResponse(
            _previa_url(oferta_id, erro=detalhe),
            status_code=303,
        )

    sucesso = "Publicação registrada e enviada."
    return RedirectResponse(
        f"/historico?canal_id={quote(canal_id)}&sucesso={quote(sucesso)}",
        status_code=303,
    )


@router.post("/ofertas/{oferta_id}/aprovar-publicar")
def aprovar_e_publicar(
    request: Request,
    oferta_id: str,
    repo: RepositorioDep,
    canal_id: Annotated[str, Form()],
) -> RedirectResponse:
    """Aprova e publica em um unico passo, direto da fila.

    Motivado pela primeira rodada de validacao: a representante relatou que
    percorrer aprovacao e publicacao em telas separadas cobrava esforco demais
    para uma decisao simples, e as duas reclamaram da lentidao entre escolher
    a oferta e ela estar publicada. Aqui as duas acoes viram uma requisicao so.
    """
    try:
        oferta = repo.get_oferta(oferta_id)
        if oferta is None:
            raise OfertaNaoEncontradaError(f"Oferta {oferta_id} nao encontrada.")
        if oferta.status is OfferStatus.PENDENTE:
            aprovar_oferta(oferta_id, repo)
        # O link era gerado e validado na tela de previa; aqui isso acontece na
        # mesma requisicao, porque a publicacao depende da validacao.
        oferta = repo.get_oferta(oferta_id)
        if oferta is not None:
            gerar_e_validar_link(
                oferta,
                request.app.state.gerador,
                request.app.state.validator,
                repo,
            )
        publicacao = publicar(
            oferta_id,
            canal_id,
            request.app.state.publicador,
            repo,
        )
    except (OfertaJaPublicadaError, PublicacaoRecusadaError, CanalNaoEncontradoError) as exc:
        return RedirectResponse(
            _previa_url(oferta_id, erro=str(exc)),
            status_code=303,
        )
    except OfertaNaoEncontradaError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if publicacao.status_envio is SendStatus.FALHA:
        detalhe = publicacao.erro_detalhe or "Falha desconhecida no envio."
        return RedirectResponse(
            _previa_url(oferta_id, erro=detalhe),
            status_code=303,
        )

    sucesso = "Oferta aprovada e publicada em um passo."
    return RedirectResponse(
        f"/?canal_id={quote(canal_id)}&sucesso={quote(sucesso)}",
        status_code=303,
    )


@router.get("/historico", response_class=HTMLResponse)
def historico(
    request: Request,
    repo: RepositorioDep,
    canal_id: str | None = None,
    page: int = 1,
    erro: str | None = None,
    sucesso: str | None = None,
) -> HTMLResponse:
    settings = request.app.state.settings
    canais = repo.listar_canais()
    selecionado = next((item for item in canais if item.id == canal_id), None)
    if selecionado is None and canais:
        selecionado = canais[0]

    filtro = selecionado.id if selecionado else None
    total = repo.contar_publicacoes(filtro)
    page, total_pages = _paginacao(page, total, settings.page_size)
    publicacoes = consultar_historico(filtro, repo, page, settings.page_size)
    itens = [
        {
            "publicacao": item,
            "oferta": repo.get_oferta(item.oferta_id),
            "canal": repo.get_canal(item.canal_id),
        }
        for item in publicacoes
    ]

    return templates.TemplateResponse(
        request=request,
        name="historico.html",
        context={
            "itens": itens,
            "canais": canais,
            "canal_selecionado": selecionado,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "erro": erro,
            "sucesso": sucesso,
        },
    )
