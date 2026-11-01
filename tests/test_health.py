"""Testes da sonda de saúde.

A sonda existe para o monitoramento e para o deploy. O teste garante que ela responde
sem depender de banco configurado, que é o contrato que o monitoramento vai consumir.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_responde_ok() -> None:
    cliente = TestClient(create_app())
    resposta = cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "servico": "radar-de-ofertas"}


def test_health_nao_exige_banco_acessivel() -> None:
    cliente = TestClient(create_app())
    corpo = cliente.get("/health").json()

    assert "database" not in corpo
    assert corpo["status"] == "ok"
