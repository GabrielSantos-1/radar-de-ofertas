"""Testes do validador de link.

O validador é o único adaptador que fala com a rede, então o teste cobre os três
desfechos que interessam ao domínio sem depender de internet: link bom, link que
responde erro e link que nem conecta. Usa mock no httpx para manter o teste
determinístico no CI.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from app.infrastructure.link_validator import HttpxLinkValidator


@pytest.fixture
def validador() -> HttpxLinkValidator:
    return HttpxLinkValidator(max_ms=5000)


def test_link_que_responde_200_e_valido(validador: HttpxLinkValidator) -> None:
    with patch("app.infrastructure.link_validator.httpx.get") as fake:
        fake.return_value = httpx.Response(200, request=httpx.Request("GET", "https://x.test/p"))

        resultado = validador.validar("https://x.test/p")

    assert resultado.status_code == 200
    assert resultado.valido is True
    assert resultado.validado_em is not None


def test_link_que_responde_404_e_invalido(validador: HttpxLinkValidator) -> None:
    with patch("app.infrastructure.link_validator.httpx.get") as fake:
        fake.return_value = httpx.Response(404, request=httpx.Request("GET", "https://x.test/p"))

        resultado = validador.validar("https://x.test/p")

    assert resultado.status_code == 404
    assert resultado.valido is False


def test_redirecionamento_para_200_e_valido(validador: HttpxLinkValidator) -> None:
    with patch("app.infrastructure.link_validator.httpx.get") as fake:
        fake.return_value = httpx.Response(301, request=httpx.Request("GET", "https://x.test/p"))

        resultado = validador.validar("https://x.test/p")

    assert resultado.status_code == 301
    assert resultado.valido is True


def test_falha_de_conexao_vira_status_zero_e_invalido(validador: HttpxLinkValidator) -> None:
    with patch("app.infrastructure.link_validator.httpx.get") as fake:
        fake.side_effect = httpx.ConnectError("sem rota para o host")

        resultado = validador.validar("https://x.test/p")

    assert resultado.status_code == 0
    assert resultado.valido is False


def test_timeout_do_http_e_tratado_como_invalido(validador: HttpxLinkValidator) -> None:
    with patch("app.infrastructure.link_validator.httpx.get") as fake:
        fake.side_effect = httpx.TimeoutException("estourou o tempo")

        resultado = validador.validar("https://x.test/p")

    assert resultado.status_code == 0
    assert resultado.valido is False


def test_validador_respeita_timeout_configurado() -> None:
    validador = HttpxLinkValidator(max_ms=1500)

    with patch("app.infrastructure.link_validator.httpx.get") as fake:
        fake.return_value = httpx.Response(200, request=httpx.Request("GET", "https://x.test/p"))
        validador.validar("https://x.test/p")

    assert fake.call_args.kwargs["timeout"] == 1.5
    assert fake.call_args.kwargs["follow_redirects"] is True
